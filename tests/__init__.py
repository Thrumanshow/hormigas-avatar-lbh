# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Las pruebas usan una clave HMAC temporal: nunca tocan ~/.hormigas-avatar/lbh.key."""
import atexit
import os
import shutil
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="lbh-tests-")
os.environ["LBH_KEY_PATH"] = str(Path(_TMP) / "test.key")
atexit.register(shutil.rmtree, _TMP, ignore_errors=True)
