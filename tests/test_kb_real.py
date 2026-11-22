# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import unittest

from lbh.knowledge import Knowledge
from tests.helpers import REPO

MAX_REGLA = 150  # con la voz actual, mas largo se acerca al limite de 15 s


class KbRealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = json.loads((REPO / "data" / "knowledge_base.json").read_text(encoding="utf-8"))

    def test_estructura_basica(self):
        self.assertIsInstance(self.kb.get("default"), str)
        self.assertIsInstance(self.kb.get("rules"), dict)
        self.assertTrue(self.kb["rules"])

    def test_reglas_son_texto_corto(self):
        for k, v in self.kb["rules"].items():
            self.assertIsInstance(v, str, k)
            self.assertTrue(v.strip(), k)
            self.assertLessEqual(len(v), MAX_REGLA, f"'{k}' tiene {len(v)} caracteres")

    def test_alias_apuntan_a_reglas_existentes(self):
        for k, lst in (self.kb.get("aliases") or {}).items():
            self.assertIn(k, self.kb["rules"], f"alias de regla inexistente: {k}")
            self.assertIsInstance(lst, list)
            self.assertTrue(all(isinstance(a, str) and a for a in lst), k)

    def test_pronunciacion_valida(self):
        pron = self.kb.get("pronunciacion") or {}
        self.assertIsInstance(pron, dict)
        for k, v in pron.items():
            self.assertTrue(isinstance(k, str) and k and isinstance(v, str) and v, k)

    def test_velocidad_valida(self):
        for k, v in (self.kb.get("velocidad") or {}).items():
            self.assertIn(k, self.kb["rules"], k)
            self.assertIsInstance(v, int)
            self.assertTrue(100 <= v <= 220, f"{k}: {v}")

    def test_cada_regla_se_responde_a_si_misma(self):
        """Detecta choques: escribir el nombre de una regla debe devolver su respuesta."""
        k = Knowledge(self.kb)
        for key, answer in self.kb["rules"].items():
            _, reply, _ = k.answer(key)
            self.assertEqual(reply, answer, f"la regla '{key}' la tapa otra regla")

    def test_contrato_human_existe(self):
        self.assertGreater((REPO / ".human").stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
