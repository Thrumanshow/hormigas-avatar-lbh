from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

from lbh.protocol import AntRole, SignalType

PHEROMONE_TAG = "kb-pheromone"

DEFAULT_KB = {
    "default": "Enjambre activo en el borde. Procesamiento local listo.",
    "rules": {
        "hormigas": "HormigasAIS coordina siete agentes ligeros con tramas LBH sin depender de nubes externas.",
        "avatar": "El avatar local sincroniza estados y visemas con audio generado en el dispositivo.",
    },
}


def norm(text: str) -> str:
    """Minusculas y sin acentos."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", norm(text))


def score(key: str, words: list[str], joined: str) -> int:
    """4 frase completa | 3 palabra exacta | 2 inicio de palabra | 1 subcadena | 0 nada."""
    k_tokens = tokens(key)
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


def kb_digest(kb: dict) -> str:
    canon = json.dumps(kb, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


class Knowledge:
    def __init__(self, kb: dict):
        self.kb = kb if isinstance(kb, dict) else dict(DEFAULT_KB)
        self.digest = kb_digest(self.kb)

    @classmethod
    def from_file(cls, path) -> "Knowledge":
        try:
            p = Path(path)
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return cls(data)
        except (OSError, json.JSONDecodeError):
            pass
        return cls(dict(DEFAULT_KB))

    def best_rule(self, text: str):
        words = tokens(text)
        joined = " ".join(words)
        aliases = self.kb.get("aliases") or {}
        best_key, best_score = None, 0
        for key, answer in (self.kb.get("rules") or {}).items():
            if not isinstance(answer, str):
                continue
            extra = aliases.get(key, [])
            if not isinstance(extra, list):
                extra = []
            sc = max(score(k, words, joined) for k in [key, *extra] if isinstance(k, str))
            if sc > best_score:  # empate: gana la primera regla del archivo
                best_key, best_score = key, sc
        return best_key, best_score

    def answer(self, text: str):
        key, sc = self.best_rule(text)
        if key is None:
            return "default", self.kb.get("default", "Listo."), 0
        return key, self.kb["rules"][key], sc

    # ---- canal de feromonas ----
    def emit_pheromone(self, bus) -> Path:
        payload = {
            "kind": "knowledge",
            "version": 1,
            "kb_sha256": self.digest,
            "rule_count": len(self.kb.get("rules") or {}),
            "kb": self.kb,
        }
        return bus.emit(AntRole.RAZONADORA, SignalType.KNOWLEDGE_PHEROMONE, payload, step_tag=PHEROMONE_TAG)

    @classmethod
    def from_pheromone(cls, bus, frame_path) -> "Knowledge":
        msg = bus.read(frame_path)  # verifica HMAC-SHA256
        if msg["role"] != AntRole.RAZONADORA or msg["sig_type"] != SignalType.KNOWLEDGE_PHEROMONE:
            raise ValueError("no es una feromona de conocimiento de la Razonadora")
        p = msg["payload"]
        kb = p.get("kb")
        if not isinstance(kb, dict) or kb_digest(kb) != p.get("kb_sha256"):
            raise ValueError("el hash de la KB no coincide con la feromona")
        return cls(kb)

    @classmethod
    def latest(cls, bus):
        pattern = f"*_02_razonadora_{PHEROMONE_TAG}.lbh"
        for path in sorted(bus.queue_dir.glob(pattern), reverse=True):
            try:
                return cls.from_pheromone(bus, path)
            except Exception:
                continue
        return None
