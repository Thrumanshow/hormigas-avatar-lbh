from __future__ import annotations

import hashlib
from pathlib import Path

from lbh.bus import LBHBus
from lbh.protocol import AntRole, SignalType

MOUTH_PATHS = {
    "REST": '<line x1="80" y1="132" x2="120" y2="132" stroke="#1e293b" stroke-width="4" stroke-linecap="round"/>',
    "A": '<ellipse cx="100" cy="134" rx="14" ry="12" fill="#991b1b" stroke="#1e293b" stroke-width="3"/>',
    "E": '<rect x="82" y="126" width="36" height="12" rx="5" fill="#991b1b" stroke="#1e293b" stroke-width="3"/>',
    "O": '<circle cx="100" cy="133" r="10" fill="#991b1b" stroke="#1e293b" stroke-width="3"/>',
    "U": '<circle cx="100" cy="133" r="7" fill="#991b1b" stroke="#1e293b" stroke-width="3"/>',
    "MBP": '<line x1="82" y1="132" x2="118" y2="132" stroke="#1e293b" stroke-width="5" stroke-linecap="round"/>',
    "FV": '<rect x="85" y="128" width="30" height="8" rx="2" fill="#f8fafc" stroke="#1e293b" stroke-width="3"/>',
    "LNT": '<path d="M84 130 Q100 142 116 130 Z" fill="#991b1b" stroke="#1e293b" stroke-width="3"/>',
}

MAX_SAMPLED_FRAMES = 24


class RenderAvatarAnt:
    def __init__(self, bus: LBHBus, frames_dir: Path, mode: str = "viseme_svg_local"):
        if mode != "viseme_svg_local":
            raise NotImplementedError(f"Modo '{mode}' aun no implementado; usa 'viseme_svg_local'")
        self.bus = bus
        self.frames_dir = Path(frames_dir)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.mode = mode

    def _build_svg(self, viseme: str, state: str, expression: str, idx: int) -> str:
        mouth = MOUTH_PATHS.get(viseme, MOUTH_PATHS["REST"])
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">'
            '<rect width="200" height="200" rx="24" fill="#0f172a"/>'
            '<circle cx="100" cy="100" r="68" fill="#f5d0a9" stroke="#38bdf8" stroke-width="3"/>'
            '<circle cx="76" cy="84" r="7" fill="#0f172a"/><circle cx="124" cy="84" r="7" fill="#0f172a"/>'
            f"{mouth}"
            '<text x="100" y="186" text-anchor="middle" fill="#94a3b8" font-size="11" font-family="monospace">'
            f"#{idx} | {viseme} | {state} | {expression}</text>"
            "</svg>"
        )

    def run(self, frame_path: Path) -> Path:
        msg = self.bus.read(frame_path)
        p = msg["payload"]
        session_id = p["session_id"]
        seq = p.get("sequence", [])

        session_frames_dir = self.frames_dir / session_id
        session_frames_dir.mkdir(parents=True, exist_ok=True)

        if seq:
            step = max(1, -(-len(seq) // MAX_SAMPLED_FRAMES))  # techo: nunca mas de 24 cuadros
            sampled = seq[::step]
        else:
            sampled = [{"t_start": 0.0, "t_end": 0.5, "viseme": "REST", "state": "idle", "expression": "neutral"}]

        generated = []
        for idx, item in enumerate(sampled):
            svg = self._build_svg(item["viseme"], item["state"], item["expression"], idx)
            f_path = session_frames_dir / f"frame_{idx:03d}_{item['viseme']}.svg"
            f_path.write_text(svg, encoding="utf-8")
            generated.append(
                {
                    "index": idx,
                    "t_start": item["t_start"],
                    "viseme": item["viseme"],
                    "frame_path": self.bus.rel(f_path),
                    "frame_sha256": hashlib.sha256(f_path.read_bytes()).hexdigest(),
                }
            )

        out_payload = {
            "session_id": session_id,
            "render_mode": self.mode,
            "wav_path": p["wav_path"],
            "wav_sha256": p["wav_sha256"],
            "duration_sec": p["duration_sec"],
            "frame_count": len(generated),
            "frames": generated,
        }
        return self.bus.emit(AntRole.RENDER_AVATAR, SignalType.AVATAR_FRAME, out_payload, step_tag=session_id)
