"""Las pruebas usan una clave HMAC temporal: nunca tocan ~/.hormigas-avatar/lbh.key."""
import atexit
import os
import shutil
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="lbh-tests-")
os.environ["LBH_KEY_PATH"] = str(Path(_TMP) / "test.key")
atexit.register(shutil.rmtree, _TMP, ignore_errors=True)
