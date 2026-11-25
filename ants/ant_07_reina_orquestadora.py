# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

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

    def _verify_verdict(self, session_id: str, avatar_path: Path, verdict_path: Path):
        """Comprueba que el veredicto es de la Vigia, de esta sesion y de ESTA trama de avatar.

        Devuelve (veredicto, avatar, fallo). fallo es None solo si todo verifica; en cualquier
        otro caso la Reina no debe entregar el paquete (falla cerrada).
        """
        try:
            verdict = self.bus.read(verdict_path)
            avatar = self.bus.read(avatar_path)
        except Exception:
            return None, None, "verdict_readable"

        if verdict["role"] != AntRole.VIGIA_CONTRATO:
            return verdict, avatar, "verdict_role"
        if verdict["sig_type"] not in (SignalType.CONTRACT_VERDICT, SignalType.ALERT):
            return verdict, avatar, "verdict_type"

        vp = verdict["payload"]
        if not isinstance(vp, dict) or vp.get("session_id") != session_id:
            return verdict, avatar, "verdict_session"

        approved = vp.get("approved")
        if not isinstance(approved, bool) or approved != (verdict["sig_type"] == SignalType.CONTRACT_VERDICT):
            return verdict, avatar, "verdict_consistency"

        if avatar["role"] != AntRole.RENDER_AVATAR or avatar["sig_type"] != SignalType.AVATAR_FRAME:
            return verdict, avatar, "avatar_frame_type"
        if not isinstance(avatar["payload"], dict) or avatar["payload"].get("session_id") != session_id:
            return verdict, avatar, "avatar_session"

        if vp.get("verified_avatar_frame_signal") != avatar["mac_hex"]:
            return verdict, avatar, "verdict_avatar_binding"

        return verdict, avatar, None

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
        verdict_msg, avatar_msg, fallo = self._verify_verdict(session_id, avatar_path, verdict_path)

        if fallo is not None:
            approved = False
            status = "HELD_UNVERIFIED_VERDICT"
            checks = {fallo: False}
            avatar_payload = {}
        else:
            approved = verdict_msg["payload"]["approved"]
            status = "READY_FOR_DELIVERY" if approved else "HELD_BY_VIGIA"
            checks = verdict_msg["payload"].get("checks", {})
            avatar_payload = avatar_msg["payload"]

        package = {
            "session_id": session_id,
            "priority": priority,
            "status": status,
            "approved": approved,
            "checks": checks,
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
