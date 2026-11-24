# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import struct
import time
from enum import IntEnum
from pathlib import Path


class AntRole(IntEnum):
    EXPLORADORA = 1
    RAZONADORA = 2
    VOZ_TTS = 3
    FONEMAS_VISEMAS = 4
    RENDER_AVATAR = 5
    VIGIA_CONTRATO = 6
    REINA_ORQUESTADORA = 7


class SignalType(IntEnum):
    INTENT_TEXT = 10
    STRUCTURED_REPLY = 20
    AUDIO_BLOCK = 30
    VISEME_SEQUENCE = 40
    AVATAR_FRAME = 50
    CONTRACT_VERDICT = 60
    SWARM_PACKAGE = 70
    KNOWLEDGE_PHEROMONE = 80
    ALERT = 99


# "LBH1" + version(1B) + role(1B) + sig_type(1B) + flags(1B) + timestamp(8B double) + payload_len(4B)
HEADER_STRUCT = struct.Struct("!4sBBBBdI")
HEADER_SIZE = HEADER_STRUCT.size  # 20 bytes
MAC_SIZE = 32
MAX_PAYLOAD = 1_000_000
MAGIC = b"LBH1"

_KEY_CACHE: bytes | None = None


def _key_path() -> Path:
    env = os.environ.get("LBH_KEY_PATH")
    return Path(env) if env else Path.home() / ".hormigas-avatar" / "lbh.key"


def get_key() -> bytes:
    """Clave HMAC local, fuera del repo. Se crea la primera vez."""
    global _KEY_CACHE
    if _KEY_CACHE is None:
        path = _key_path()
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(secrets.token_bytes(32))
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
        _KEY_CACHE = path.read_bytes()
    return _KEY_CACHE


def _mac(data: bytes) -> bytes:
    return hmac.new(get_key(), data, hashlib.sha256).digest()


def encode_lbh_frame(role: AntRole, sig_type: SignalType, payload: dict, flags: int = 0) -> bytes:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(body) > MAX_PAYLOAD:
        raise ValueError("Carga util LBH demasiado grande")
    header = HEADER_STRUCT.pack(
        MAGIC, 1, int(role), int(sig_type), flags & 0xFF, time.time(), len(body)
    )
    return header + body + _mac(header + body)


def decode_lbh_frame(raw: bytes) -> dict:
    if len(raw) < HEADER_SIZE + MAC_SIZE:
        raise ValueError("Trama LBH incompleta")

    header = raw[:HEADER_SIZE]
    magic, version, role, sig_type, flags, ts, length = HEADER_STRUCT.unpack(header)
    if magic != MAGIC:
        raise ValueError("Cabecera LBH invalida")
    if version != 1:
        raise ValueError("Version LBH no soportada")
    if length > MAX_PAYLOAD:
        raise ValueError("Longitud de carga util LBH excesiva")

    body_end = HEADER_SIZE + length
    mac_end = body_end + MAC_SIZE
    if len(raw) != mac_end:
        raise ValueError("Longitud de trama LBH inconsistente")

    body = raw[HEADER_SIZE:body_end]
    mac = raw[body_end:mac_end]
    if not hmac.compare_digest(mac, _mac(header + body)):
        raise ValueError("Fallo de autenticacion HMAC-SHA256 en trama LBH")

    return {
        "version": version,
        "role": AntRole(role),
        "role_name": AntRole(role).name,
        "sig_type": SignalType(sig_type),
        "sig_name": SignalType(sig_type).name,
        "flags": flags,
        "timestamp": ts,
        "mac_hex": mac.hex(),
        "payload": json.loads(body.decode("utf-8")),
    }
