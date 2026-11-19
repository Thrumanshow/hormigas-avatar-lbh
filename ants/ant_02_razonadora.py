from __future__ import annotations

from pathlib import Path

from lbh.bus import LBHBus
from lbh.knowledge import Knowledge
from lbh.protocol import AntRole, SignalType


class RazonadoraAnt:
    def __init__(self, bus: LBHBus, kb_path: Path):
        self.bus = bus
        self.kb_path = Path(kb_path)
        self.knowledge = Knowledge.from_file(self.kb_path)
        self.kb = self.knowledge.kb
        # Feromona: comparte la KB firmada con el resto del enjambre
        self.pheromone_path = self.knowledge.emit_pheromone(bus)

    def run(self, frame_path: Path) -> Path:
        msg = self.bus.read(frame_path)
        p = msg["payload"]
        matched_rule, reply, score = self.knowledge.answer(p.get("normalized_text", ""))

        out_payload = {
            "session_id": p["session_id"],
            "intent": p["intent"],
            "matched_rule": matched_rule,
            "match_score": score,
            "kb_sha256": self.knowledge.digest,
            "reply_text": reply[:220],
            "expression_hint": "focused" if p["intent"] == "query" else "welcoming",
        }
        return self.bus.emit(
            AntRole.RAZONADORA, SignalType.STRUCTURED_REPLY, out_payload, step_tag=p["session_id"]
        )
