from datetime import datetime, timezone
from .database import Database
class MigrationRunner:
    def __init__(self,database): self.database=database
    def upgrade(self):
        self.database.open()
        db = self.database.connection
        assert db is not None
        db.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied_at_utc TEXT NOT NULL)")
        if not db.execute("SELECT 1 FROM schema_migrations WHERE version=1").fetchone():
            db.executescript("""
                CREATE TABLE paired_devices(device_id TEXT PRIMARY KEY,label TEXT NOT NULL,public_key_b64 TEXT NOT NULL,signing_public_key_b64 TEXT NOT NULL,created_at_utc TEXT NOT NULL,last_seen_at_utc TEXT,revoked_at_utc TEXT,metadata_json TEXT NOT NULL DEFAULT '{}');
                CREATE TABLE sessions(session_id TEXT PRIMARY KEY,device_id TEXT NOT NULL,key_salt_b64 TEXT NOT NULL,created_at_utc TEXT NOT NULL,last_seen_at_utc TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('active','revoked','expired')),revoked_reason TEXT,FOREIGN KEY(device_id) REFERENCES paired_devices(device_id));
                CREATE TABLE security_events(id INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT NOT NULL UNIQUE,timestamp_utc TEXT NOT NULL,severity TEXT NOT NULL CHECK(severity IN ('low','medium','high','critical')),category TEXT NOT NULL,event_type TEXT NOT NULL,session_id TEXT,device_id TEXT,reason TEXT NOT NULL,evidence_json TEXT NOT NULL DEFAULT '{}',previous_hash TEXT,record_hash TEXT NOT NULL UNIQUE);
                CREATE TABLE audit_chain_state(id INTEGER PRIMARY KEY CHECK(id=1),head_hash TEXT,updated_at_utc TEXT NOT NULL);
                INSERT INTO audit_chain_state VALUES(1,NULL,datetime('now'));
                CREATE TABLE calibration_runs(run_id TEXT PRIMARY KEY,calibration_type TEXT NOT NULL,label TEXT,started_at_utc TEXT NOT NULL,ended_at_utc TEXT,sample_count INTEGER NOT NULL DEFAULT 0,dataset_sha256 TEXT,status TEXT NOT NULL CHECK(status IN ('running','complete','failed')),metadata_json TEXT NOT NULL DEFAULT '{}');
                CREATE TABLE model_registry(model_name TEXT PRIMARY KEY,model_version TEXT NOT NULL,feature_schema_json TEXT NOT NULL,dataset_sha256 TEXT NOT NULL,sample_count INTEGER NOT NULL DEFAULT 0 CHECK(sample_count>=0),metrics_json TEXT NOT NULL DEFAULT '{}',artifact_path TEXT NOT NULL,trained_at_utc TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('calibrating','ready','retired')));
                CREATE UNIQUE INDEX idx_one_active_session ON sessions(status) WHERE status='active';
                CREATE INDEX idx_events_timestamp ON security_events(timestamp_utc);
                """)
            db.execute("INSERT INTO schema_migrations VALUES(1,?,?)",("tracepulse_schema_v1",datetime.now(timezone.utc).isoformat()))
            db.commit()