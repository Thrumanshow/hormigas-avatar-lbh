from __future__ import annotations

import json
import re
import unicodedata
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


def _norm(text: str) -> str:
    """Minusculas y sin acentos."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", _norm(text))


def _score(key: str, words: list[str], joined: str) -> int:
    """4 frase completa | 3 palabra exacta | 2 inicio de palabra | 1 subcadena | 0 nada."""
    k_tokens = _tokens(key)
    if not k_tokens:
        return 0
    k = " ".join(k_tokens)
    if len(k_tokens) > 1:
        return 4 if f" {k} " in f" {joined} " else 0
    best = 0
    for w in words:
        if w == k:
            return 3
        if w.startswith(k):
            best = max(best, 2)
        elif k in w:
            best = max(best, 1)
    return best


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

    def _best_rule(self, text: str):
        words = _tokens(text)
        joined = " ".join(words)
        aliases = self.kb.get("aliases", {}) or {}
        best_key, best_score = None, 0
        for key, answer in self.kb.get("rules", {}).items():
            if not isinstance(answer, str):
                continue
            extra = aliases.get(key, []) if isinstance(aliases.get(key, []), list) else []
            score = max(_score(k, words, joined) for k in [key, *extra])
            if score > best_score:  # empate: gana la primera regla del archivo
                best_key, best_score = key, score
        return best_key, best_score

    def run(self, frame_path: Path) -> Path:
        msg = self.bus.read(frame_path)
        p = msg["payload"]

        key, score = self._best_rule(p.get("normalized_text", ""))
        if key is None:
            reply, matched_rule = self.kb.get("default", "Listo."), "default"
        else:
            reply, matched_rule = self.kb["rules"][key], key

        out_payload = {
            "session_id": p["session_id"],
            "intent": p["intent"],
            "matched_rule": matched_rule,
            "match_score": score,
            "reply_text": reply[:220],
            "expression_hint": "focused" if p["intent"] == "query" else "welcoming",
        }
        return self.bus.emit(
            AntRole.RAZONADORA, SignalType.STRUCTURED_REPLY, out_payload, step_tag=p["session_id"]
        )
