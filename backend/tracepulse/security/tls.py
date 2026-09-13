import ssl
from pathlib import Path
class TlsConfigurationError(ValueError): pass
def server_context(cert_file,key_file):
    cert,key=Path(cert_file),Path(key_file)
    if not cert.is_file() or not key.is_file(): raise TlsConfigurationError("TLS files are missing")
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.minimum_version=ssl.TLSVersion.TLSv1_3; context.maximum_version=ssl.TLSVersion.TLSv1_3; context.load_cert_chain(str(cert),str(key)); return context
def client_context(ca_file,hostname):
    if not Path(ca_file).is_file() or not hostname: raise TlsConfigurationError("CA and hostname are required")
    context=ssl.create_default_context(ssl.Purpose.SERVER_AUTH,cafile=str(ca_file)); context.minimum_version=ssl.TLSVersion.TLSv1_3; context.maximum_version=ssl.TLSVersion.TLSv1_3; context.check_hostname=True; return context