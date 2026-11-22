# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import time
from pathlib import Path

from lbh.protocol import AntRole, SignalType, decode_lbh_frame, encode_lbh_frame


class LBHBus:
    def __init__(self, base_dir: Path, max_frames: int = 300, max_log_bytes: int = 512 * 1024):
        self.base_dir = Path(base_dir).resolve()
        self.queue_dir = self.base_dir / "avatars" / "output" / "bus_frames"
        self.log_path = self.base_dir / "logs" / "swarm_bus.log"
        self.max_frames = max_frames
        self.max_log_bytes = max_log_bytes
        self._seq = 0
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    # --- rutas relativas a la raiz del repo ---
    def rel(self, path) -> str:
        p = Path(path)
        try:
            return p.resolve().relative_to(self.base_dir).as_posix()
        except ValueError:
            return str(p)

    def resolve(self, path) -> Path:
        p = Path(path)
        return p if p.is_absolute() else self.base_dir / p

    def is_inside(self, path) -> bool:
        try:
            self.resolve(path).resolve().relative_to(self.base_dir)
            return True
        except ValueError:
            return False

    # --- limpieza para que no crezca sin limite ---
    def maintenance(self) -> None:
        frames = sorted(self.queue_dir.glob("*.lbh"))
        for old in frames[: max(0, len(frames) - self.max_frames)]:
            old.unlink(missing_ok=True)
        if self.log_path.exists() and self.log_path.stat().st_size > self.max_log_bytes:
            self.log_path.replace(self.log_path.with_suffix(".log.1"))

    def emit(self, role: AntRole, sig_type: SignalType, payload: dict, step_tag: str = "") -> Path:
        frame = encode_lbh_frame(role, sig_type, payload)
        self._seq += 1
        fname = f"{int(time.time() * 1000)}_{self._seq:04d}_{role.value:02d}_{role.name.lower()}_{step_tag}.lbh"
        out_path = self.queue_dir / fname
        out_path.write_bytes(frame)

        decoded = decode_lbh_frame(frame)
        log_line = (
            f"{decoded['timestamp']:.3f} | ant={role.value}:{role.name} | "
            f"sig={sig_type.name} | mac={decoded['mac_hex'][:16]} | file={out_path.name}\n"
        )
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(log_line)
        return out_path

    def read(self, frame_path: Path) -> dict:
        return decode_lbh_frame(Path(frame_path).read_bytes())
