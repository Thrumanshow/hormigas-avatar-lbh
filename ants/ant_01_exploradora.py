from __future__ import annotations

import re
from pathlib import Path

from lbh.bus import LBHBus
from lbh.protocol import AntRole, SignalType


class ExploradoraAnt:
    def __init__(self, bus: LBHBus, max_chars: int = 280):
        self.bus = bus
        self.max_chars = max_chars

    def run(self, raw_input: str, session_id: str = "sess-01") -> Path:
        # El id de sesion se usa en nombres de archivo: solo caracteres seguros
        session_id = re.sub(r"[^A-Za-z0-9_-]", "", session_id or "")[:40] or "sess-01"
        cleaned = re.sub(r"\s+", " ", (raw_input or "").strip())

        reason = ""
        if not cleaned:
            reason = "entrada vacia"
        elif len(cleaned) > self.max_chars:
            reason = f"entrada supera {self.max_chars} caracteres"
        valid = not reason

        intent = "greeting" if any(w in cleaned.lower() for w in ("hola", "buenas", "qué tal", "que tal")) else "query"
        payload = {
            "session_id": session_id,
            "valid_context": valid,
            "reason": reason,
            "intent": intent,
            "normalized_text": cleaned[: self.max_chars],
            "char_count": len(cleaned),
        }
        sig = SignalType.INTENT_TEXT if valid else SignalType.ALERT
        return self.bus.emit(AntRole.EXPLORADORA, sig, payload, step_tag=session_id)
