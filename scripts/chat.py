# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import shutil
import subprocess
import sys
import time
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

try:
    import readline  # noqa: F401  (historial con flechas, si existe)
except ImportError:
    pass

MAX_CHARS = 280
KEEP_SESSIONS = 5


def limpiar_sesiones(out_dir: Path, keep: int = KEEP_SESSIONS) -> int:
    """Borra sesiones chat-* antiguas (wav, paquete y cuadros). Conserva las ultimas `keep`."""
    wavs = sorted(out_dir.glob("chat-*_voice.wav"), key=lambda p: p.stat().st_mtime)
    viejas = wavs[:-keep] if len(wavs) > keep else []
    for wav in viejas:
        sid = wav.name[: -len("_voice.wav")]
        wav.unlink(missing_ok=True)
        (out_dir / f"{sid}_package.json").unlink(missing_ok=True)
        shutil.rmtree(out_dir / "frames" / sid, ignore_errors=True)
    return len(viejas)


def detener(player: str | None) -> None:
    if player:
        try:
            subprocess.run([player, "stop"], capture_output=True, timeout=10)
        except (subprocess.TimeoutExpired, OSError):
            pass


def reproducir(player: str | None, wav: Path) -> None:
    if not player:
        return
    detener(player)  # un unico reproductor: corta el audio anterior
    try:
        subprocess.run([player, "play", str(wav)], capture_output=True, timeout=10)
    except (subprocess.TimeoutExpired, OSError):
        print("  (no pude lanzar el reproductor)")


def main() -> int:
    human = ROOT / ".human"
    if not human.exists() or human.stat().st_size == 0:
        print("ERROR: falta el contrato .human (o esta vacio). El enjambre no arranca sin el.")
        return 1

    import os

    bus = LBHBus(ROOT)
    bus.maintenance()
    out_dir = ROOT / "avatars" / "output"
    piper_model = os.environ.get("PIPER_MODEL")

    a1 = ExploradoraAnt(bus, max_chars=MAX_CHARS)
    a2 = RazonadoraAnt(bus, ROOT / "data" / "knowledge_base.json")
    a3 = VozTTSAnt(bus, out_dir, Path(piper_model) if piper_model else None)
    a4 = FonemasVisemasAnt(bus)
    a5 = RenderAvatarAnt(bus, out_dir / "frames")
    a6 = VigiaContratoAnt(bus, human)
    a7 = ReinaOrquestadoraAnt(bus, out_dir)

    player = shutil.which("termux-media-player")
    silencio = player is None
    borradas = limpiar_sesiones(out_dir)

    print("Chat con el avatar de las hormigas  |  /ayuda para comandos")
    if player is None:
        print("(termux-media-player no encontrado: sin reproduccion; el audio queda en avatars/output/)")
    if borradas:
        print(f"(limpieza: {borradas} sesiones antiguas eliminadas)")

    base = int(time.time())
    turno = 0
    ultimo: dict = {}

    while True:
        try:
            texto = input("\ntu> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not texto:
            continue

        if texto.startswith("/"):
            cmd = texto.lower()
            if cmd in ("/salir", "/exit", "/q"):
                break
            if cmd == "/ayuda":
                print("  /salir     termina el chat")
                print("  /silencio  activa o desactiva la reproduccion de audio")
                print("  /stats     motor de voz y resultado de la Vigia del ultimo turno")
            elif cmd == "/silencio":
                if player is None:
                    print("  No hay reproductor disponible (instala Termux:API y: pkg install termux-api).")
                else:
                    silencio = not silencio
                    if silencio:
                        detener(player)
                    print("  Audio:", "silenciado" if silencio else "activado")
            elif cmd == "/stats":
                if not ultimo:
                    print("  Aun no hay turnos.")
                else:
                    for k, v in ultimo.items():
                        print(f"  {k}: {v}")
                    print(f"  turnos: {turno} | audio: {'silenciado' if silencio else 'activado'}")
            else:
                print("  Comando desconocido. Prueba /ayuda")
            continue

        if len(texto) > MAX_CHARS:
            print(f"  Aviso: {len(texto)} caracteres; el maximo es {MAX_CHARS}. Acortalo e intenta de nuevo.")
            continue

        turno += 1
        sid = f"chat-{base}-{turno}"
        try:
            f1 = a1.run(texto, session_id=sid)
            m1 = bus.read(f1)
            if m1["sig_type"] == SignalType.ALERT:
                print("  Exploradora rechazo la entrada:", m1["payload"].get("reason"))
                turno -= 1
                continue
            sid = m1["payload"]["session_id"]

            f2 = a2.run(f1)
            f3 = a3.run(f2)
            f4 = a4.run(f3)
            f5 = a5.run(f4)
            f6 = a6.run([f1, f2, f3, f4, f5])
            pkg = a7.consolidate(sid, 1, f1, f2, f3, f4, f5, f6)

            respuesta = bus.read(f2)["payload"]["reply_text"]
            motor = bus.read(f3)["payload"]["engine"]
            fallidos = [k for k, v in pkg["checks"].items() if not v]
            ultimo = {
                "sesion": sid,
                "motor_voz": motor,
                "estado": pkg["status"],
                "duracion_s": pkg["duration_sec"],
                "cuadros": pkg["frame_count"],
                "chequeos_fallidos": fallidos or "ninguno",
            }

            if pkg["approved"]:
                print(f"avatar> {respuesta}")
                if not silencio:
                    reproducir(player, ROOT / pkg["wav_path"])
            else:
                print("  La Vigia retuvo el paquete. Chequeos fallidos:", fallidos)
        except Exception as exc:  # un turno fallido no tumba el chat
            print(f"  Error en el ciclo: {exc}")
            turno -= 1
            continue

        limpiar_sesiones(out_dir)
        bus.maintenance()

    detener(player)
    print("Hasta luego.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
