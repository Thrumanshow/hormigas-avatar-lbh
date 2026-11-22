from __future__ import annotations

import hashlib
import math
import re
import shutil
import subprocess
import sys
import wave
from array import array
from pathlib import Path

from lbh.bus import LBHBus
from lbh.knowledge import Knowledge
from lbh.protocol import AntRole, SignalType

DEFAULT_RATE = 160


class VozTTSAnt:
    """Motores en orden: piper_local -> espeak_local -> stdlib_tone_fallback.
    Pronunciacion y velocidad llegan por feromona (campos 'pronunciacion' y 'velocidad' de la KB)."""

    def __init__(self, bus: LBHBus, output_dir: Path, piper_model: Path | None = None,
                 espeak_voice: str | None = None):
        import os
        self.bus = bus
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.piper_model = Path(piper_model) if piper_model else None
        self.espeak_voice = espeak_voice or os.environ.get("ESPEAK_VOICE", "es-419")
        self._knowledge = None

    # ---- conocimiento recibido por feromona ----
    def _kb_dict(self) -> dict:
        if self._knowledge is None:
            self._knowledge = Knowledge.latest(self.bus)
        return self._knowledge.kb if self._knowledge else {}

    def spoken_text(self, text: str) -> str:
        """Texto que se lee en voz alta (la pantalla conserva el original)."""
        pron = self._kb_dict().get("pronunciacion") or {}
        if not isinstance(pron, dict):
            return text
        keys = [k for k, v in pron.items() if isinstance(k, str) and k and isinstance(v, str)]
        for k in sorted(keys, key=len, reverse=True):
            repl = pron[k]
            text = re.sub(re.escape(k), lambda m, r=repl: r, text, flags=re.IGNORECASE)
        return text

    def rate_for(self, rule) -> int:
        vel = self._kb_dict().get("velocidad") or {}
        v = vel.get(rule) if isinstance(vel, dict) else None
        if isinstance(v, int) and 100 <= v <= 220:
            return v
        return DEFAULT_RATE

    # ---- utilidades ----
    def _wav_duration(self, wav_path: Path) -> float:
        with wave.open(str(wav_path), "rb") as wf:
            rate = wf.getframerate()
            return round(wf.getnframes() / float(rate), 3) if rate else 0.0

    def _wav_ok(self, wav_path: Path) -> bool:
        try:
            return wav_path.exists() and wav_path.stat().st_size > 44 and self._wav_duration(wav_path) > 0
        except (wave.Error, EOFError, OSError):
            return False

    # ---- motores ----
    def _try_piper(self, text: str, wav_path: Path) -> bool:
        piper_bin = shutil.which("piper")
        if not (piper_bin and self.piper_model and self.piper_model.exists()):
            return False
        wav_path.unlink(missing_ok=True)
        cmd = [piper_bin, "--model", str(self.piper_model), "--output_file", str(wav_path)]
        try:
            proc = subprocess.run(cmd, input=text.encode("utf-8"), capture_output=True, timeout=60)
        except (subprocess.TimeoutExpired, OSError):
            return False
        return proc.returncode == 0 and self._wav_ok(wav_path)

    def _try_espeak(self, text: str, wav_path: Path, rate: int = DEFAULT_RATE) -> bool:
        binary = shutil.which("espeak-ng") or shutil.which("espeak")
        if not binary:
            return False
        for voice in dict.fromkeys([self.espeak_voice, "es"]):
            wav_path.unlink(missing_ok=True)
            cmd = [binary, "-v", voice, "-s", str(rate), "-w", str(wav_path), "--stdin"]
            try:
                proc = subprocess.run(cmd, input=text.encode("utf-8"), capture_output=True, timeout=30)
            except (subprocess.TimeoutExpired, OSError):
                continue
            if proc.returncode == 0 and self._wav_ok(wav_path):
                return True
        return False

    def _synthesize_fallback_wav(self, text: str, wav_path: Path) -> None:
        sample_rate = 16000
        duration_sec = max(0.8, min(8.0, len(text) / 11.0))
        total = int(sample_rate * duration_sec)

        samples = array("h")
        for i in range(total):
            t = i / sample_rate
            env = 0.5 + 0.5 * math.sin(2 * math.pi * 4.2 * t)
            fade = min(1.0, i / 400.0, (total - i) / 400.0)
            samples.append(int(2200 * env * fade * math.sin(2 * math.pi * 195.0 * t)))
        if sys.byteorder == "big":
            samples.byteswap()

        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(samples.tobytes())

    # ---- ciclo ----
    def run(self, frame_path: Path) -> Path:
        msg = self.bus.read(frame_path)
        p = msg["payload"]
        session_id = p["session_id"]
        text = p["reply_text"]
        spoken = self.spoken_text(text)
        rate = self.rate_for(p.get("matched_rule"))
        wav_path = self.output_dir / f"{session_id}_voice.wav"

        if self._try_piper(spoken, wav_path):
            engine = "piper_local"
        elif self._try_espeak(spoken, wav_path, rate):
            engine = "espeak_local"
        else:
            wav_path.unlink(missing_ok=True)
            self._synthesize_fallback_wav(spoken, wav_path)
            engine = "stdlib_tone_fallback"

        duration = self._wav_duration(wav_path)
        wav_sha256 = hashlib.sha256(wav_path.read_bytes()).hexdigest()

        out_payload = {
            "session_id": session_id,
            "reply_text": text,
            "spoken_text": spoken,
            "expression_hint": p.get("expression_hint", "neutral"),
            "engine": engine,
            "espeak_rate": rate,
            "wav_path": self.bus.rel(wav_path),
            "wav_sha256": wav_sha256,
            "duration_sec": duration,
        }
        return self.bus.emit(AntRole.VOZ_TTS, SignalType.AUDIO_BLOCK, out_payload, step_tag=session_id)
