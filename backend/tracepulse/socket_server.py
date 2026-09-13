from __future__ import annotations
from flask import request
from .security.message_integrity import MessageEnvelope,MessageIntegrityError,sign_message,verify_message
from .security.replay_guard import ReplayGuard
class SecureSocketServer:
    def __init__(self,socketio,services): self.socketio=socketio; self.services=services; self.guards={}
    def register(self):
        @self.socketio.on("connect")
        def connect(): return self.services.config.testing or request.environ.get("wsgi.url_scheme")=="https"
        @self.socketio.on("secure_message")
        def secure_message(raw):
            try:
                envelope=MessageEnvelope.from_mapping(raw); session=self.services.sessions.require_active(envelope.session_id); verify_message(envelope,key=session.key,expected_session_id=session.session_id); self.guards.setdefault(session.session_id,ReplayGuard()).check_and_record(envelope); self.services.sessions.touch(session.session_id)
                for reply in self.services.handle_message(session,envelope.event,envelope.payload,envelope.sequence):
                    signed=sign_message(key=session.key,session_id=session.session_id,sequence=self.services.sessions.next_outbound_sequence(session.session_id),event=reply["event"],payload=reply.get("payload",{})); self.socketio.emit("secure_message",signed.as_dict(),to=request.sid)
                return {"ok":True}
            except Exception:
                self.services.audit.append(severity="high",category="message",event_type="rejected",reason="authenticated message rejected",evidence={"remote":request.remote_addr}); return {"ok":False,"error":"authenticated message rejected"}