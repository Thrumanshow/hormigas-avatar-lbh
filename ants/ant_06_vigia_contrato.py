from __future__ import annotations

import hashlib
from pathlib import Path

from lbh.bus import LBHBus
from lbh.protocol import AntRole, SignalType

EXPECTED_CHAIN = [
    (AntRole.EXPLORADORA, SignalType.INTENT_TEXT),
    (AntRole.RAZONADORA, SignalType.STRUCTURED_REPLY),
    (AntRole.VOZ_TTS, SignalType.AUDIO_BLOCK),
    (AntRole.FONEMAS_VISEMAS, SignalType.VISEME_SEQUENCE),
    (AntRole.RENDER_AVATAR, SignalType.AVATAR_FRAME),
]


class VigiaContratoAnt:
    def __init__(self, bus: LBHBus, human_file: Path, max_frames: int = 60, max_duration_sec: float = 15.0):
        self.bus = bus
        self.human_file = Path(human_file)
        self.max_frames = max_frames
        self.max_duration_sec = max_duration_sec

    def _check_chain(self, chain: list[Path], session_id: str) -> bool:
        """Verifica HMAC, rol, tipo y sesion de cada trama previa, y coherencia del hash del audio."""
        try:
            if len(chain) != len(EXPECTED_CHAIN):
                return False
            wav_hashes = set()
            for path, (role, sig) in zip(chain, EXPECTED_CHAIN):
                m = self.bus.read(path)
                if m["role"] != role or m["sig_type"] != sig:
                    return False
                if m["payload"].get("session_id") != session_id:
                    return False
                if m["payload"].get("wav_sha256"):
                    wav_hashes.add(m["payload"]["wav_sha256"])
            return len(wav_hashes) == 1
        except Exception:
            return False

    def run(self, chain: list[Path]) -> Path:
        """chain = [intent, reply, audio, viseme, avatar] en ese orden."""
        try:
            msg = self.bus.read(chain[-1])
            p = msg["payload"]
            session_id = p["session_id"]
        except Exception:
            out = {"session_id": "unknown", "approved": False, "checks": {"avatar_frame_readable": False}}
            return self.bus.emit(AntRole.VIGIA_CONTRATO, SignalType.ALERT, out, step_tag="unknown")

        human_ok = self.human_file.exists() and self.human_file.stat().st_size > 0
        checks = {
            "human_contract_present": human_ok,
            "chain_integrity": self._check_chain(chain, session_id),
            "duration_within_limit": float(p.get("duration_sec", 0.0)) <= self.max_duration_sec,
            "frame_count_within_limit": int(p.get("frame_count", 0)) <= self.max_frames,
            "audio_hash_intact": False,
            "all_frames_intact": True,
        }

        wav_rel = p.get("wav_path", "")
        if wav_rel and self.bus.is_inside(wav_rel):
            wav_file = self.bus.resolve(wav_rel)
            if wav_file.exists():
                actual = hashlib.sha256(wav_file.read_bytes()).hexdigest()
                checks["audio_hash_intact"] = actual == p.get("wav_sha256")

        for fr in p.get("frames", []):
            fr_rel = fr.get("frame_path", "")
            if not fr_rel or not self.bus.is_inside(fr_rel):
                checks["all_frames_intact"] = False
                break
            fp = self.bus.resolve(fr_rel)
            if not fp.exists() or hashlib.sha256(fp.read_bytes()).hexdigest() != fr.get("frame_sha256"):
                checks["all_frames_intact"] = False
                break

        approved = all(checks.values())
        sig_type = SignalType.CONTRACT_VERDICT if approved else SignalType.ALERT
        out_payload = {
            "session_id": session_id,
            "approved": approved,
            "checks": checks,
            "verified_avatar_frame_signal": msg["mac_hex"],
        }
        return self.bus.emit(AntRole.VIGIA_CONTRATO, sig_type, out_payload, step_tag=session_id)
