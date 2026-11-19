from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ants.ant_01_exploradora import ExploradoraAnt
from ants.ant_02_razonadora import RazonadoraAnt
from ants.ant_03_voz_tts import VozTTSAnt
from ants.ant_04_fonemas_visemas import FonemasVisemasAnt
from ants.ant_05_render_avatar import RenderAvatarAnt
from ants.ant_06_vigia_contrato import VigiaContratoAnt
from ants.ant_07_reina_orquestadora import ReinaOrquestadoraAnt
from lbh.bus import LBHBus
from lbh.protocol import SignalType


def main() -> int:
    human_path = ROOT / ".human"
    if not human_path.exists() or human_path.stat().st_size == 0:
        print("ERROR: falta el contrato .human (o esta vacio). El enjambre no arranca sin el.")
        return 1

    text = sys.argv[1] if len(sys.argv) > 1 else "Hola, ¿cómo funciona el avatar de hormigas?"
    session_id = sys.argv[2] if len(sys.argv) > 2 else "demo-001"

    bus = LBHBus(ROOT)
    bus.maintenance()
    out_dir = ROOT / "avatars" / "output"
    piper_model = os.environ.get("PIPER_MODEL")

    a1 = ExploradoraAnt(bus)
    a2 = RazonadoraAnt(bus, ROOT / "data" / "knowledge_base.json")
    a3 = VozTTSAnt(bus, out_dir, Path(piper_model) if piper_model else None)
    a4 = FonemasVisemasAnt(bus)
    a5 = RenderAvatarAnt(bus, out_dir / "frames")
    a6 = VigiaContratoAnt(bus, human_path)
    a7 = ReinaOrquestadoraAnt(bus, out_dir)

    f1 = a1.run(text, session_id=session_id)
    m1 = bus.read(f1)
    if m1["sig_type"] == SignalType.ALERT:
        print("Exploradora rechazo la entrada:", m1["payload"].get("reason"))
        return 2
    session_id = m1["payload"]["session_id"]  # ya saneado

    f2 = a2.run(f1)
    f3 = a3.run(f2)
    f4 = a4.run(f3)
    f5 = a5.run(f4)
    f6 = a6.run([f1, f2, f3, f4, f5])
    pkg = a7.consolidate(session_id, 1, f1, f2, f3, f4, f5, f6)

    print("Estado final:", pkg["status"], "| Cuadros:", pkg["frame_count"], "| Duracion:", pkg["duration_sec"], "s")
    print("Audio:", pkg["wav_path"])
    if not pkg["approved"]:
        failed = [k for k, v in pkg["checks"].items() if not v]
        print("Vigia retuvo el paquete. Chequeos fallidos:", failed)
        return 3
    print("Reproducir: termux-media-player play", ROOT / pkg["wav_path"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
