from __future__ import annotations

import re
from pathlib import Path

from lbh.bus import LBHBus
from lbh.knowledge import Knowledge
from lbh.protocol import AntRole, SignalType


class ExploradoraAnt:
    def __init__(self, bus: LBHBus, max_chars: int = 280, knowledge: Knowledge | None = None):
        self.bus = bus
        self.max_chars = max_chars
        self._knowledge = knowledge

    def _kb(self):
        """Adopta la ultima feromona de conocimiento valida (se guarda en cache)."""
        if self._knowledge is None:
            self._knowledge = Knowledge.latest(self.bus)
        return self._knowledge

    def run(self, raw_input: str, session_id: str = "sess-01") -> Path:
        session_id = re.sub(r"[^A-Za-z0-9_-]", "", session_id or "")[:40] or "sess-01"
        cleaned = re.sub(r"\s+", " ", (raw_input or "").strip())

        reason = ""
        if not cleaned:
            reason = "entrada vacia"
        elif len(cleaned) > self.max_chars:
            reason = f"entrada supera {self.max_chars} caracteres"
        valid = not reason

        topic, kb_sha = None, None
        if valid:
            k = self._kb()
            if k is not None:
                topic = k.best_rule(cleaned)[0]
                kb_sha = k.digest

        intent = "greeting" if any(w in cleaned.lower() for w in ("hola", "buenas", "qué tal", "que tal")) else "query"
        payload = {
            "session_id": session_id,
            "valid_context": valid,
            "reason": reason,
            "intent": intent,
            "topic": topic,
            "kb_sha256": kb_sha,
            "normalized_text": cleaned[: self.max_chars],
            "char_count": len(cleaned),
        }
        sig = SignalType.INTENT_TEXT if valid else SignalType.ALERT
        return self.bus.emit(AntRole.EXPLORADORA, sig, payload, step_tag=session_id)
