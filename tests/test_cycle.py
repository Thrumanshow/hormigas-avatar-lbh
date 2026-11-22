import unittest

from lbh.knowledge import Knowledge
from lbh.protocol import SignalType
from tests.helpers import build_ants, make_root, run_until_render


class CycleTests(unittest.TestCase):
    def setUp(self):
        self.root = make_root(self)
        self.ns = build_ants(self.root)

    def verdict(self, chain):
        return self.ns.bus.read(self.ns.a6.run(chain))

    def test_ciclo_completo_aprobado(self):
        chain = run_until_render(self.ns, "¿Qué es el nodo?", "c1")
        f6 = self.ns.a6.run(chain)
        v = self.ns.bus.read(f6)
        self.assertEqual(v["sig_type"], SignalType.CONTRACT_VERDICT)
        self.assertTrue(all(v["payload"]["checks"].values()), v["payload"]["checks"])
        self.assertIn("knowledge_in_sync", v["payload"]["checks"])
        pkg = self.ns.a7.consolidate("c1", 1, *chain, f6)
        self.assertEqual(pkg["status"], "READY_FOR_DELIVERY")
        self.assertTrue((self.ns.out / "c1_package.json").exists())

    def test_cuadro_alterado_bloquea(self):
        chain = run_until_render(self.ns, "¿Qué es el nodo?", "c2")
        rel = self.ns.bus.read(chain[4])["payload"]["frames"][0]["frame_path"]
        fp = self.ns.bus.resolve(rel)
        fp.write_text(fp.read_text(encoding="utf-8") + "<!-- alterado -->", encoding="utf-8")
        v = self.verdict(chain)
        self.assertEqual(v["sig_type"], SignalType.ALERT)
        self.assertFalse(v["payload"]["checks"]["all_frames_intact"])

    def test_audio_alterado_bloquea(self):
        chain = run_until_render(self.ns, "¿Qué es el nodo?", "c3")
        wav = self.ns.bus.resolve(self.ns.bus.read(chain[4])["payload"]["wav_path"])
        with wav.open("ab") as fh:
            fh.write(b"x")
        v = self.verdict(chain)
        self.assertFalse(v["payload"]["checks"]["audio_hash_intact"])
        self.assertFalse(v["payload"]["approved"])

    def test_sin_contrato_human_bloquea(self):
        chain = run_until_render(self.ns, "¿Qué es el nodo?", "c4")
        (self.root / ".human").unlink()
        v = self.verdict(chain)
        self.assertFalse(v["payload"]["checks"]["human_contract_present"])
        self.assertFalse(v["payload"]["approved"])

    def test_cadena_desordenada_bloquea(self):
        chain = run_until_render(self.ns, "¿Qué es el nodo?", "c5")
        chain[1], chain[2] = chain[2], chain[1]
        v = self.verdict(chain)
        self.assertFalse(v["payload"]["checks"]["chain_integrity"])

    def test_conocimiento_distinto_bloquea(self):
        otra = Knowledge({"default": "x", "rules": {"nodo": "otra respuesta"}})
        ns = build_ants(make_root(self), explorer_knowledge=otra)
        chain = run_until_render(ns, "¿Qué es el nodo?", "c6")
        v = ns.bus.read(ns.a6.run(chain))
        self.assertFalse(v["payload"]["checks"]["knowledge_in_sync"])
        self.assertFalse(v["payload"]["approved"])


if __name__ == "__main__":
    unittest.main()
