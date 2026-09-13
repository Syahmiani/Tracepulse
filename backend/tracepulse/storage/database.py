from __future__ import annotations
import os, sqlite3, threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

class DatabaseError(RuntimeError): pass

@dataclass(frozen=True)
class DatabaseConfig: path:Path; busy_timeout_ms:int=5000
class Database:
    def __init__(self,config): self.path=Path(config.path).expanduser().resolve(); self.timeout=config.busy_timeout_ms; self.lock=threading.RLock(); self.connection=None
    def open(self):
        with self.lock:
            if self.connection: return
            self.path.parent.mkdir(parents=True,exist_ok=True); os.chmod(self.path.parent,0o700)
            self.connection=sqlite3.connect(self.path,timeout=self.timeout/1000,isolation_level=None,check_same_thread=False); self.connection.row_factory=sqlite3.Row
            for pragma in ("PRAGMA foreign_keys=ON","PRAGMA journal_mode=WAL","PRAGMA synchronous=FULL","PRAGMA secure_delete=ON",f"PRAGMA busy_timeout={self.timeout}"): self.connection.execute(pragma)
            os.chmod(self.path,0o600)
    def close(self):
        with self.lock:
            if self.connection: self.connection.close(); self.connection=None
    def _db(self):
        if not self.connection: raise RuntimeError("database is not open")
        return self.connection
    @contextmanager
    def transaction(self)->Iterator[sqlite3.Connection]:
        with self.lock:
            db=self._db(); db.execute("BEGIN IMMEDIATE")
            try: yield db; db.execute("COMMIT")
            except Exception: db.execute("ROLLBACK"); raise
    def fetch_one(self,sql,parameters:Sequence[object]=()):
        with self.lock: return self._db().execute(sql,parameters).fetchone()
    def fetch_all(self,sql,parameters:Sequence[object]=()):
        with self.lock: return self._db().execute(sql,parameters).fetchall()
    def initialize(self):
        from .migrations import MigrationRunner
        MigrationRunner(self).upgrade()