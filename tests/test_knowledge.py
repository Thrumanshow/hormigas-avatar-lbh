# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import unittest
from pathlib import Path

from lbh.bus import LBHBus
from lbh.knowledge import Knowledge, PHEROMONE_TAG, kb_digest, norm
from lbh.protocol import AntRole, SignalType
from tests.helpers import FIXTURE_KB, make_root


class MatchTests(unittest.TestCase):
    def setUp(self):
        self.k = Knowledge(FIXTURE_KB)

    def rule(self, text):
        return self.k.best_rule(text)[0]

    def test_palabra_exacta(self):
        self.assertEqual(self.rule("¿Qué es el nodo?"), "nodo")

    def test_frase_gana_a_palabra_exacta(self):
        self.assertEqual(self.rule("¿Qué es el LBH SDK?"), "lbh-sdk")
        self.assertEqual(self.rule("¿Qué significa LBH?"), "significado")
        self.assertEqual(self.rule("Lenguaje Binario HormigasAIS"), "significado")

    def test_alias_exacto(self):
        self.assertEqual(self.rule("Háblame del sdk"), "lbh-sdk")

    def test_palabra_exacta_gana_a_inicio_de_palabra(self):
        self.assertEqual(self.rule("¿Qué es HormigasAIS?"), "hormigasais")
        self.assertEqual(self.rule("Las hormigas trabajan"), "hormigas")

    def test_empate_gana_la_primera_regla_del_archivo(self):
        orden = list(FIXTURE_KB["rules"])
        esperado = min(("nodo", "centinela"), key=orden.index)
        self.assertEqual(self.rule("El centinela en el nodo"), esperado)

    def test_sin_coincidencia_usa_default(self):
        self.assertEqual(self.k.answer("zzz sin relación"), ("default", "Respuesta por defecto.", 0))

    def test_acentos_y_mayusculas(self):
        self.assertEqual(norm("Hóla ÁÉ"), "hola ae")

    def test_reglas_no_texto_se_ignoran(self):
        k = Knowledge({"rules": {"a": 123, "b": "ok"}})
        self.assertEqual(k.best_rule("a b")[0], "b")

    def test_kb_invalida_cae_al_default(self):
        self.assertIn("rules", Knowledge([]).kb)

    def test_from_file_ausente_o_corrupto(self):
        root = make_root(self)
        self.assertIn("rules", Knowledge.from_file(root / "no-existe.json").kb)
        mala = root / "mala.json"
        mala.write_text("{no es json", encoding="utf-8")
        self.assertIn("rules", Knowledge.from_file(mala).kb)

    def test_digest_estable_y_sensible(self):
        a = {"x": 1, "y": {"b": 2, "a": 3}}
        b = {"y": {"a": 3, "b": 2}, "x": 1}
        self.assertEqual(kb_digest(a), kb_digest(b))
        self.assertNotEqual(kb_digest(a), kb_digest({"x": 2, "y": {"b": 2, "a": 3}}))


class PheromoneTests(unittest.TestCase):
    def setUp(self):
        self.root = make_root(self)
        self.bus = LBHBus(self.root)
        self.k = Knowledge(FIXTURE_KB)

    def test_sin_feromonas_no_hay_conocimiento(self):
        self.assertIsNone(Knowledge.latest(self.bus))

    def test_emitir_y_adoptar(self):
        path = self.k.emit_pheromone(self.bus)
        got = Knowledge.from_pheromone(self.bus, path)
        self.assertEqual(got.digest, self.k.digest)
        self.assertEqual(got.kb["default"], FIXTURE_KB["default"])

    def test_trama_alterada_se_rechaza(self):
        path = self.k.emit_pheromone(self.bus)
        raw = bytearray(path.read_bytes())
        raw[30] ^= 0xFF
        mala = self.bus.queue_dir / "alterada.lbh"
        mala.write_bytes(bytes(raw))
        with self.assertRaises(ValueError):
            Knowledge.from_pheromone(self.bus, mala)

    def test_hash_falso_con_firma_valida_se_rechaza(self):
        falsa = self.bus.emit(
            AntRole.RAZONADORA, SignalType.KNOWLEDGE_PHEROMONE,
            {"kind": "knowledge", "version": 1, "kb_sha256": "0" * 64, "rule_count": 0,
             "kb": {"default": "x", "rules": {}}}, step_tag="falsa")
        with self.assertRaises(ValueError):
            Knowledge.from_pheromone(self.bus, falsa)

    def test_rol_equivocado_se_rechaza(self):
        intruso = self.bus.emit(
            AntRole.EXPLORADORA, SignalType.KNOWLEDGE_PHEROMONE,
            {"kind": "knowledge", "version": 1, "kb_sha256": self.k.digest,
             "rule_count": 1, "kb": self.k.kb}, step_tag="intruso")
        with self.assertRaises(ValueError):
            Knowledge.from_pheromone(self.bus, intruso)

    def test_latest_salta_las_invalidas(self):
        self.k.emit_pheromone(self.bus)  # valida
        # mas reciente pero con hash falso, y con la etiqueta que latest() busca
        self.bus.emit(
            AntRole.RAZONADORA, SignalType.KNOWLEDGE_PHEROMONE,
            {"kind": "knowledge", "version": 1, "kb_sha256": "0" * 64, "rule_count": 0,
             "kb": {"default": "x", "rules": {}}}, step_tag=PHEROMONE_TAG)
        got = Knowledge.latest(self.bus)
        self.assertIsNotNone(got)
        self.assertEqual(got.digest, self.k.digest)


if __name__ == "__main__":
    unittest.main()
