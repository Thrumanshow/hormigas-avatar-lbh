from __future__ import annotations

import json
from pathlib import Path

from lbh.bus import LBHBus
from lbh.protocol import AntRole, SignalType

DEFAULT_KB = {
    "default": "Enjambre activo en el borde. Procesamiento local listo.",
    "rules": {
        "hormigas": "HormigasAIS coordina siete agentes ligeros con tramas LBH sin depender de nubes externas.",
        "avatar": "El avatar local sincroniza estados y visemas con audio generado en el dispositivo.",
    },
}


class RazonadoraAnt:
    def __init__(self, bus: LBHBus, kb_path: Path):
        self.bus = bus
        self.kb_path = Path(kb_path)
        self.kb = self._load_kb()

    def _load_kb(self) -> dict:
        try:
            if self.kb_path.exists():
                data = json.loads(self.kb_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
        except (OSError, json.JSONDecodeError):
            pass
        return DEFAULT_KB

    def run(self, frame_path: Path) -> Path:
        msg = self.bus.read(frame_path)
        p = msg["payload"]
        lower = p.get("normalized_text", "").lower()

        reply = self.kb.get("default", "Listo.")
        matched_rule = "default"
        for key, answer in self.kb.get("rules", {}).items():
            if key in lower:
                reply = answer
                matched_rule = key
                break

        out_payload = {
            "session_id": p["session_id"],
            "intent": p["intent"],
            "matched_rule": matched_rule,
            "reply_text": reply[:220],
            "expression_hint": "focused" if p["intent"] == "query" else "welcoming",
        }
        return self.bus.emit(
            AntRole.RAZONADORA, SignalType.STRUCTURED_REPLY, out_payload, step_tag=p["session_id"]
        )
