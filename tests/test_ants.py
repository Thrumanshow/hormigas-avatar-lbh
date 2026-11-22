import hashlib
import unittest

from ants.ant_01_exploradora import ExploradoraAnt
from ants.ant_05_render_avatar import RenderAvatarAnt
from lbh.bus import LBHBus
from lbh.protocol import AntRole, SignalType
from tests.helpers import build_ants, make_root


class ExploradoraTests(unittest.TestCase):
    def setUp(self):
        self.root = make_root(self)
        self.ns = build_ants(self.root)

    def payload(self, text, sid="e1"):
        return self.ns.bus.read(self.ns.a1.run(text, sid))

    def test_entrada_vacia_es_alerta(self):
        m = self.payload("")
        self.assertEqual(m["sig_type"], SignalType.ALERT)
        self.assertFalse(m["payload"]["valid_context"])

    def test_entrada_larga_es_alerta(self):
        self.assertEqual(self.payload("a" * 281)["sig_type"], SignalType.ALERT)

    def test_limite_exacto_es_valido(self):
        self.assertEqual(self.payload("a" * 280)["sig_type"], SignalType.INTENT_TEXT)

    def test_id_de_sesion_se_sanea(self):
        self.assertEqual(self.payload("hola", "../../x y")["payload"]["session_id"], "xy")

    def test_adopta_la_feromona_y_clasifica_tema(self):
        m = self.payload("¿Qué es el nodo?")
        self.assertEqual(m["payload"]["topic"], "nodo")
        self.assertEqual(m["payload"]["kb_sha256"], self.ns.a2.knowledge.digest)

    def test_sin_coincidencia_no_hay_tema(self):
        self.assertIsNone(self.payload("zzz sin relación")["payload"]["topic"])

    def test_sin_feromona_no_adopta_nada(self):
        bus = LBHBus(make_root(self))  # bus sin ninguna feromona
        m = bus.read(ExploradoraAnt(bus).run("hola", "e2"))
        self.assertIsNone(m["payload"]["kb_sha256"])
        self.assertIsNone(m["payload"]["topic"])


class FonemasRenderTests(unittest.TestCase):
    def setUp(self):
        self.root = make_root(self)
        self.ns = build_ants(self.root)

    def test_acentos_y_enie_mapean_bien(self):
        f = self.ns.bus.emit(
            AntRole.VOZ_TTS, SignalType.AUDIO_BLOCK,
            {"session_id": "v1", "reply_text": "áéñ", "expression_hint": "neutral",
             "wav_path": "x.wav", "wav_sha256": "0", "duration_sec": 3.0}, step_tag="v1")
        seq = self.ns.bus.read(self.ns.a4.run(f))["payload"]["sequence"]
        self.assertEqual([s["viseme"] for s in seq], ["A", "E", "LNT"])

    def test_render_respeta_el_tope_de_cuadros(self):
        item = {"t_start": 0.0, "t_end": 0.1, "viseme": "A", "state": "speaking", "expression": "neutral"}
        f = self.ns.bus.emit(
            AntRole.FONEMAS_VISEMAS, SignalType.VISEME_SEQUENCE,
            {"session_id": "r1", "wav_path": "x.wav", "wav_sha256": "0", "duration_sec": 3.0,
             "sequence": [dict(item) for _ in range(100)]}, step_tag="r1")
        p = self.ns.bus.read(self.ns.a5.run(f))["payload"]
        self.assertTrue(1 <= p["frame_count"] <= 24)

    def test_render_rechaza_modos_no_implementados(self):
        with self.assertRaises(NotImplementedError):
            RenderAvatarAnt(self.ns.bus, self.root / "f", mode="remote_gpu_node")


class VozTests(unittest.TestCase):
    def setUp(self):
        self.root = make_root(self)
        self.ns = build_ants(self.root)

    def test_pronunciacion_desde_la_feromona(self):
        v = self.ns.a3
        self.assertEqual(v.spoken_text("HormigasAIS y LBH-SDK"), "hormigas ais y LBH SDK")
        self.assertEqual(v.spoken_text("hormigasais"), "hormigas ais")
        self.assertEqual(v.spoken_text("El nodo A16"), "El nodo A16")

    def test_velocidad_por_regla(self):
        v = self.ns.a3
        self.assertEqual(v.rate_for("lbh-sdk"), 140)
        self.assertEqual(v.rate_for("nodo"), 160)
        self.assertEqual(v.rate_for(None), 160)

    def test_audio_generado_y_hash_correcto(self):
        f1 = self.ns.a1.run("¿Qué es el nodo?", "voz1")
        f3 = self.ns.a3.run(self.ns.a2.run(f1))
        p = self.ns.bus.read(f3)["payload"]
        self.assertIn(p["engine"], {"piper_local", "espeak_local", "stdlib_tone_fallback"})
        wav = self.ns.bus.resolve(p["wav_path"])
        self.assertTrue(wav.exists())
        self.assertEqual(hashlib.sha256(wav.read_bytes()).hexdigest(), p["wav_sha256"])
        self.assertGreater(p["duration_sec"], 0)


if __name__ == "__main__":
    unittest.main()
