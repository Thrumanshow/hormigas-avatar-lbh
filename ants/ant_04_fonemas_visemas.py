from __future__ import annotations

import unicodedata
from pathlib import Path

from lbh.bus import LBHBus
from lbh.protocol import AntRole, SignalType

CHAR_TO_VISEME = {
    "a": "A",
    "e": "E", "i": "E",
    "o": "O",
    "u": "U",
    "m": "MBP", "b": "MBP", "p": "MBP",
    "f": "FV", "v": "FV",
    "l": "LNT", "n": "LNT", "t": "LNT", "d": "LNT",
}
DEFAULT_CONSONANT = "LNT"


def _normalize(text: str) -> str:
    """Quita acentos y dieresis (a, e, i, o, u, n) antes del mapeo."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


class FonemasVisemasAnt:
    def __init__(self, bus: LBHBus):
        self.bus = bus

    def run(self, frame_path: Path) -> Path:
        msg = self.bus.read(frame_path)
        p = msg["payload"]
        text = p.get("reply_text", "")
        duration = float(p.get("duration_sec", 1.0))
        expr = p.get("expression_hint", "neutral")

        tokens = [ch for ch in _normalize(text) if ch.isalpha() or ch.isspace()]
        step_dt = duration / max(1, len(tokens))

        sequence = []
        cursor = 0.0
        for ch in tokens:
            viseme = "REST" if ch.isspace() else CHAR_TO_VISEME.get(ch, DEFAULT_CONSONANT)
            state = "speaking" if viseme != "REST" else "idle_breath"
            sequence.append(
                {
                    "t_start": round(cursor, 3),
                    "t_end": round(min(duration, cursor + step_dt), 3),
                    "viseme": viseme,
                    "state": state,
                    "expression": expr,
                }
            )
            cursor += step_dt

        out_payload = {
            "session_id": p["session_id"],
            "wav_path": p["wav_path"],
            "wav_sha256": p["wav_sha256"],
            "duration_sec": duration,
            "viseme_count": len(sequence),
            "sequence": sequence,
        }
        return self.bus.emit(
            AntRole.FONEMAS_VISEMAS, SignalType.VISEME_SEQUENCE, out_payload, step_tag=p["session_id"]
        )
