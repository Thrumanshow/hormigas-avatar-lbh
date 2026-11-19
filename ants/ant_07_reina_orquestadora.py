from __future__ import annotations

import json
from pathlib import Path

from lbh.bus import LBHBus
from lbh.protocol import AntRole, SignalType


class ReinaOrquestadoraAnt:
    def __init__(self, bus: LBHBus, output_dir: Path):
        self.bus = bus
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def consolidate(
        self,
        session_id: str,
        priority: int,
        intent_path: Path,
        reply_path: Path,
        audio_path: Path,
        viseme_path: Path,
        avatar_path: Path,
        verdict_path: Path,
    ) -> dict:
        verdict_msg = self.bus.read(verdict_path)
        approved = bool(verdict_msg["payload"].get("approved", False))
        avatar_payload = self.bus.read(avatar_path)["payload"]

        status = "READY_FOR_DELIVERY" if approved else "HELD_BY_VIGIA"
        package = {
            "session_id": session_id,
            "priority": priority,
            "status": status,
            "approved": approved,
            "checks": verdict_msg["payload"].get("checks", {}),
            "wav_path": avatar_payload.get("wav_path"),
            "duration_sec": avatar_payload.get("duration_sec"),
            "frame_count": avatar_payload.get("frame_count"),
            "frames": avatar_payload.get("frames", []),
            "signals": {
                "intent": intent_path.name,
                "reply": reply_path.name,
                "audio": audio_path.name,
                "viseme": viseme_path.name,
                "avatar": avatar_path.name,
                "verdict": verdict_path.name,
            },
        }

        manifest_path = self.output_dir / f"{session_id}_package.json"
        manifest_path.write_text(json.dumps(package, indent=2, ensure_ascii=False), encoding="utf-8")

        self.bus.emit(
            AntRole.REINA_ORQUESTADORA,
            SignalType.SWARM_PACKAGE,
            {
                "session_id": session_id,
                "priority": priority,
                "status": status,
                "manifest_path": self.bus.rel(manifest_path),
            },
            step_tag=session_id,
        )
        return package
