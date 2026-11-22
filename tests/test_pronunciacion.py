# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import unittest

from tests.helpers import FIXTURE_KB, build_ants, make_root


class PronunciacionTests(unittest.TestCase):
    def voz(self, pron):
        root = make_root(self)
        kb = dict(FIXTURE_KB)
        kb["pronunciacion"] = pron
        (root / "data" / "knowledge_base.json").write_text(
            json.dumps(kb, ensure_ascii=False), encoding="utf-8"
        )
        return build_ants(root).a3

    def test_solo_palabras_completas(self):
        v = self.voz({"VERI": "beri"})
        self.assertEqual(v.spoken_text("VERI verifica y verifican"), "beri verifica y verifican")

    def test_siglas_de_tramas(self):
        v = self.voz({"ERRR": "error", "ACKK": "ak", "SEAL": "sil", "SYNC": "sinc", "PING": "pin"})
        self.assertEqual(v.spoken_text("ACKK confirma y ERRR avisa errores"), "ak confirma y error avisa errores")
        self.assertEqual(v.spoken_text("SEAL sella, SYNC sincroniza, PING mide"), "sil sella, sinc sincroniza, pin mide")

    def test_con_puntuacion_y_minusculas(self):
        v = self.voz({"ERRR": "error"})
        self.assertEqual(v.spoken_text("(ERRR), errr."), "(error), error.")

    def test_no_toca_palabras_que_contienen_la_clave(self):
        v = self.voz({"PING": "pin"})
        self.assertEqual(v.spoken_text("mapping y pingüino"), "mapping y pingüino")


if __name__ == "__main__":
    unittest.main()
