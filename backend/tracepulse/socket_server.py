from __future__ import annotations
import time
from flask import current_app, request
from .security.message_integrity import MessageEnvelope,MessageIntegrityError,sign_message,verify_message
from .security.replay_guard import ReplayGuard
from .security.sessions import SessionError

# Reasons python-engineio hands to the "disconnect" handler. A page refresh or
# tab close produces a clean shutdown ("transport close"/"client disconnect")
# that fires synchronously while handling an actual incoming HTTP request, so
# Flask-SocketIO can resolve a request context for it and our handler below
# runs normally. Wi-Fi/connectivity loss instead surfaces as "ping timeout" or
# "transport error", raised from Socket.IO's own background ping-monitor
# thread with no HTTP request in flight -- Flask-SocketIO can't resolve a
# request context for that case and silently drops the event before any
# handler (including this one) ever sees it. So connectivity loss is instead
# detected independently in Services.watchdog(), off the phone's own
# heartbeat staleness, and is intentionally ignored here if it ever does
# arrive, rather than treating a possibly-incomplete event as an unpair.
_CONNECTIVITY_LOST_REASONS = {"ping timeout", "transport error"}

class SecureSocketServer:
    def __init__(self,socketio,services):
        self.socketio=socketio; self.services=services; self.guards={}; self.session_for_sid={}
        # session_id -> {"since": monotonic seconds, "reason": str} -- pending auto-unpair
        # for a clean disconnect (tab refreshed/closed), given a short grace period to
        # reconnect before we actually revoke the pairing.
        self.pending_unpairs={}
    def _unpair_active_session(self,*,reason):
        # Mirrors api/pairing_routes.py's /api/pairing/reset so a dropped
        # authenticated socket (e.g. the phone tab refreshing or closing)
        # revokes the bond the same way pressing UNPAIR does.
        try:
            self.services.pairing.reset()
            self.services.sessions.revoke(reason)
            self.services.sessions.reset()
            with self.services.db.transaction() as conn:
                conn.execute("UPDATE sessions SET status='revoked',revoked_reason=? WHERE status='active'",(reason,))
            self.services.audit.append(severity="high",category="session",event_type="auto_unpair",reason=reason,evidence={})
        except Exception:
            self.services.app.logger.exception("auto-unpair on disconnect failed")
    def process_pending_disconnects(self,*,now=None):
        # Called from Services.watchdog() every ~0.1s so the grace period below
        # applies regardless of which thread handled the socket.io "disconnect" event.
        if not self.pending_unpairs: return
        current=time.monotonic() if now is None else now
        for session_id,pending in list(self.pending_unpairs.items()):
            active=self.services.sessions.active()
            if active is None or active.session_id!=session_id:
                # Session already gone (e.g. unpaired some other way); nothing left to do.
                self.pending_unpairs.pop(session_id,None); continue
            if current-pending["since"]>=self.services.config.phone_refresh_unpair_delay_seconds:
                self.pending_unpairs.pop(session_id,None)
                self._unpair_active_session(reason=pending["reason"])
    def register(self):
        @self.socketio.on("connect")
        def connect(): return self.services.config.testing or request.environ.get("wsgi.url_scheme")=="https"
        @self.socketio.on("disconnect")
        def disconnect(reason=None):
            session_id=self.session_for_sid.pop(request.sid,None)
            if session_id is None: return
            self.guards.pop(session_id,None)
            active=self.services.sessions.active()
            if active is None or active.session_id!=session_id: return
            if reason in _CONNECTIVITY_LOST_REASONS: return
            # Clean shutdown: likely the phone browser tab was refreshed or closed.
            # Give it a short grace period to reconnect before treating it as an unpair.
            self.pending_unpairs[session_id]={"since":time.monotonic(),"reason":f"phone socket disconnected ({reason or 'tab closed or refreshed'})"}
        @self.socketio.on("secure_message")
        def secure_message(raw):
            try:
                envelope=MessageEnvelope.from_mapping(raw); session=self.services.sessions.require_active(envelope.session_id); verify_message(envelope,key=session.key,expected_session_id=session.session_id); self.guards.setdefault(session.session_id,ReplayGuard()).check_and_record(envelope); self.services.sessions.touch(session.session_id)
                self.session_for_sid[request.sid]=session.session_id
                self.pending_unpairs.pop(session.session_id,None)
                for reply in self.services.handle_message(session,envelope.event,envelope.payload,envelope.sequence):
                    signed=sign_message(key=session.key,session_id=session.session_id,sequence=self.services.sessions.next_outbound_sequence(session.session_id),event=reply["event"],payload=reply.get("payload",{})); self.socketio.emit("secure_message",signed.as_dict(),to=request.sid)
                return {"ok":True}
            except Exception as exc:
                current_app.logger.exception("secure message rejected: %s", exc)
                self.services.audit.append(severity="high",category="message",event_type="rejected",reason="authenticated message rejected",evidence={"remote":request.remote_addr}); return {"ok":False,"error":"session expired; pair again" if isinstance(exc,SessionError) else "authenticated message rejected"}
