from __future__ import annotations
from flask import current_app, request
from .security.message_integrity import MessageEnvelope,MessageIntegrityError,sign_message,verify_message
from .security.replay_guard import ReplayGuard
from .security.sessions import SessionError
class SecureSocketServer:
    def __init__(self,socketio,services): self.socketio=socketio; self.services=services; self.guards={}; self.session_for_sid={}
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
            current_app.logger.exception("auto-unpair on disconnect failed")
    def register(self):
        @self.socketio.on("connect")
        def connect(): return self.services.config.testing or request.environ.get("wsgi.url_scheme")=="https"
        @self.socketio.on("disconnect")
        def disconnect():
            session_id=self.session_for_sid.pop(request.sid,None)
            if session_id is None: return
            self.guards.pop(session_id,None)
            active=self.services.sessions.active()
            if active is not None and active.session_id==session_id:
                self._unpair_active_session(reason="phone socket disconnected (tab closed or refreshed)")
        @self.socketio.on("secure_message")
        def secure_message(raw):
            try:
                envelope=MessageEnvelope.from_mapping(raw); session=self.services.sessions.require_active(envelope.session_id); verify_message(envelope,key=session.key,expected_session_id=session.session_id); self.guards.setdefault(session.session_id,ReplayGuard()).check_and_record(envelope); self.services.sessions.touch(session.session_id)
                self.session_for_sid[request.sid]=session.session_id
                for reply in self.services.handle_message(session,envelope.event,envelope.payload,envelope.sequence):
                    signed=sign_message(key=session.key,session_id=session.session_id,sequence=self.services.sessions.next_outbound_sequence(session.session_id),event=reply["event"],payload=reply.get("payload",{})); self.socketio.emit("secure_message",signed.as_dict(),to=request.sid)
                return {"ok":True}
            except Exception as exc:
                current_app.logger.exception("secure message rejected: %s", exc)
                self.services.audit.append(severity="high",category="message",event_type="rejected",reason="authenticated message rejected",evidence={"remote":request.remote_addr}); return {"ok":False,"error":"session expired; pair again" if isinstance(exc,SessionError) else "authenticated message rejected"}
