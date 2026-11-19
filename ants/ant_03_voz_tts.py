from __future__ import annotations

import hashlib
import math
import shutil
import subprocess
import sys
import wave
from array import array
from pathlib import Path

from lbh.bus import LBHBus
from lbh.protocol import AntRole, SignalType


class VozTTSAnt:
    def __init__(self, bus: LBHBus, output_dir: Path, piper_model: Path | None = None):
        self.bus = bus
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.piper_model = Path(piper_model) if piper_model else None

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

    def _wav_duration(self, wav_path: Path) -> float:
        with wave.open(str(wav_path), "rb") as wf:
            rate = wf.getframerate()
            return round(wf.getnframes() / float(rate), 3) if rate else 0.0

    def run(self, frame_path: Path) -> Path:
        msg = self.bus.read(frame_path)
        p = msg["payload"]
        session_id = p["session_id"]
        text = p["reply_text"]
        wav_path = self.output_dir / f"{session_id}_voice.wav"

        engine = "stdlib_tone_fallback"
        piper_bin = shutil.which("piper")
        used_piper = False
        if piper_bin and self.piper_model and self.piper_model.exists():
            cmd = [piper_bin, "--model", str(self.piper_model), "--output_file", str(wav_path)]
            try:
                proc = subprocess.run(cmd, input=text.encode("utf-8"), capture_output=True, timeout=60)
                used_piper = proc.returncode == 0 and wav_path.exists()
            except (subprocess.TimeoutExpired, OSError):
                used_piper = False
        if used_piper:
            engine = "piper_local"
        else:
            self._synthesize_fallback_wav(text, wav_path)

        duration = self._wav_duration(wav_path)
        wav_sha256 = hashlib.sha256(wav_path.read_bytes()).hexdigest()

        out_payload = {
            "session_id": session_id,
            "reply_text": text,
            "expression_hint": p.get("expression_hint", "neutral"),
            "engine": engine,
            "wav_path": self.bus.rel(wav_path),
            "wav_sha256": wav_sha256,
            "duration_sec": duration,
        }
        return self.bus.emit(AntRole.VOZ_TTS, SignalType.AUDIO_BLOCK, out_payload, step_tag=session_id)
