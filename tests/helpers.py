# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ants.ant_01_exploradora import ExploradoraAnt
from ants.ant_02_razonadora import RazonadoraAnt
from ants.ant_03_voz_tts import VozTTSAnt
from ants.ant_04_fonemas_visemas import FonemasVisemasAnt
from ants.ant_05_render_avatar import RenderAvatarAnt
from ants.ant_06_vigia_contrato import VigiaContratoAnt
from ants.ant_07_reina_orquestadora import ReinaOrquestadoraAnt
from lbh.bus import LBHBus

REPO = Path(__file__).resolve().parent.parent

FIXTURE_KB = {
    "default": "Respuesta por defecto.",
    "rules": {
        "lbh": "Regla lbh.",
        "lbh-sdk": "Regla sdk.",
        "nodo": "Regla nodo.",
        "centinela": "Regla centinela.",
        "hormigas": "Regla hormigas.",
        "hormigasais": "Regla hormigasais.",
        "significado": "Regla significado.",
    },
    "aliases": {
        "lbh-sdk": ["sdk", "lbhsdk"],
        "significado": ["que significa lbh", "lenguaje binario"],
    },
    "pronunciacion": {"HormigasAIS": "hormigas ais", "LBH-SDK": "LBH SDK"},
    "velocidad": {"lbh-sdk": 140},
}


def make_root(case: unittest.TestCase) -> Path:
    """Repo temporal con .human y una KB de prueba; se borra solo al terminar."""
    root = Path(tempfile.mkdtemp(prefix="lbh-root-"))
    case.addCleanup(shutil.rmtree, root, True)
    (root / ".human").write_text("contrato de prueba\n", encoding="utf-8")
    (root / "data").mkdir()
    (root / "data" / "knowledge_base.json").write_text(
        json.dumps(FIXTURE_KB, ensure_ascii=False), encoding="utf-8"
    )
    return root


def build_ants(root: Path, explorer_knowledge=None) -> SimpleNamespace:
    bus = LBHBus(root)
    out = root / "avatars" / "output"
    a2 = RazonadoraAnt(bus, root / "data" / "knowledge_base.json")  # emite la feromona
    return SimpleNamespace(
        root=root, bus=bus, out=out, a2=a2,
        a1=ExploradoraAnt(bus, knowledge=explorer_knowledge),
        a3=VozTTSAnt(bus, out),
        a4=FonemasVisemasAnt(bus),
        a5=RenderAvatarAnt(bus, out / "frames"),
        a6=VigiaContratoAnt(bus, root / ".human"),
        a7=ReinaOrquestadoraAnt(bus, out),
    )


def run_until_render(ns, text: str, sid: str) -> list:
    f1 = ns.a1.run(text, sid)
    f2 = ns.a2.run(f1)
    f3 = ns.a3.run(f2)
    f4 = ns.a4.run(f3)
    f5 = ns.a5.run(f4)
    return [f1, f2, f3, f4, f5]
