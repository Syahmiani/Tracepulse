from __future__ import annotations
import hashlib,hmac,json,uuid
from dataclasses import dataclass
from datetime import datetime,timezone
class AuditLog:
    def __init__(self,database): self.db=database
    @staticmethod
    def _hash(previous,record): return hashlib.sha256((previous or "").encode()+json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    def append(self,*,severity,category,event_type,reason,evidence=None,session_id=None,device_id=None):
        if severity not in {"low","medium","high","critical"} or not reason.strip(): raise ValueError("invalid audit event")
        event_id=uuid.uuid4().hex; timestamp=datetime.now(timezone.utc).isoformat(); safe=dict(evidence or {})
        with self.db.transaction() as db:
            previous=(db.execute("SELECT head_hash FROM audit_chain_state WHERE id=1").fetchone() or [None])[0]
            record={"event_id":event_id,"timestamp_utc":timestamp,"severity":severity,"category":category,"event_type":event_type,"session_id":session_id,"device_id":device_id,"reason":reason,"evidence":safe}; record_hash=self._hash(previous,record)
            db.execute("INSERT INTO security_events(event_id,timestamp_utc,severity,category,event_type,session_id,device_id,reason,evidence_json,previous_hash,record_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(event_id,timestamp,severity,category,event_type,session_id,device_id,reason,json.dumps(safe,sort_keys=True,separators=(",",":")),previous,record_hash)); db.execute("UPDATE audit_chain_state SET head_hash=?,updated_at_utc=? WHERE id=1",(record_hash,timestamp))
        return record
    def verify(self):
        rows=self.db.fetch_all("SELECT event_id,timestamp_utc,severity,category,event_type,session_id,device_id,reason,evidence_json,previous_hash,record_hash FROM security_events ORDER BY id")
        previous=None
        for row in rows:
            try: evidence=json.loads(row["evidence_json"])
            except Exception: return False
            record={"event_id":row["event_id"],"timestamp_utc":row["timestamp_utc"],"severity":row["severity"],"category":row["category"],"event_type":row["event_type"],"session_id":row["session_id"],"device_id":row["device_id"],"reason":row["reason"],"evidence":evidence}
            if row["previous_hash"]!=previous or not hmac.compare_digest(self._hash(previous,record),row["record_hash"]): return False
            previous=row["record_hash"]
        stored=(self.db.fetch_one("SELECT head_hash FROM audit_chain_state WHERE id=1") or [None])[0]
        return stored==previous