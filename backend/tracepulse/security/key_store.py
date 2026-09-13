from __future__ import annotations
import base64,json,os,secrets,tempfile
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
class KeyStoreError(RuntimeError): pass
class FileKeyStore:
    def __init__(self,path,master_key):
        if len(master_key)!=32: raise KeyStoreError("master key must be 32 bytes")
        self.path=Path(path).expanduser().resolve(); self.key=bytes(master_key); self.path.parent.mkdir(parents=True,exist_ok=True); os.chmod(self.path.parent,0o700)
        if self.path.exists() and self.path.stat().st_mode & 0o077: raise KeyStoreError("key store permissions are too broad")
    def _read(self):
        if not self.path.exists(): return {"version":1,"entries":{}}
        value=json.loads(self.path.read_text());
        if value.get("version")!=1 or not isinstance(value.get("entries"),dict): raise KeyStoreError("invalid key store")
        return value
    def set_bytes(self,name,value):
        if not name or "/" in name or "\\" in name: raise KeyStoreError("invalid key name")
        nonce=secrets.token_bytes(12); encrypted=AESGCM(self.key).encrypt(nonce,bytes(value),name.encode()); doc=self._read(); doc["entries"][name]={"nonce":base64.urlsafe_b64encode(nonce).decode(),"value":base64.urlsafe_b64encode(encrypted).decode()}; self._write(doc)
    def get_bytes(self,name):
        item=self._read()["entries"].get(name)
        if item is None:return None
        try:return AESGCM(self.key).decrypt(base64.urlsafe_b64decode(item["nonce"]),base64.urlsafe_b64decode(item["value"]),name.encode())
        except Exception as exc:raise KeyStoreError("key decryption failed") from exc
    def _write(self,doc):
        fd,tmp=tempfile.mkstemp(dir=self.path.parent,prefix=".tracepulse-"); os.fchmod(fd,0o600)
        with os.fdopen(fd,"w") as handle: json.dump(doc,handle,sort_keys=True); handle.write("\\n")
        os.replace(tmp,self.path); os.chmod(self.path,0o600)