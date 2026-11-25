# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import unittest

from lbh.protocol import AntRole, SignalType
from tests.helpers import build_ants, make_root, run_until_render


class ReinaVerificaVeredictoTests(unittest.TestCase):
    def setUp(self):
        self.ns = build_ants(make_root(self))
        self.chain = run_until_render(self.ns, "¿Qué es el nodo?", "r1")

    def _mac_avatar(self, chain):
        return self.ns.bus.read(chain[4])["mac_hex"]

    def _emitir(self, role, sig, **cambios):
        payload = {
            "session_id": "r1",
            "approved": True,
            "checks": {},
            "verified_avatar_frame_signal": self._mac_avatar(self.chain),
        }
        payload.update(cambios)
        return self.ns.bus.emit(role, sig, payload, step_tag="forjado")

    def _consolidar(self, verdict, chain=None, sid="r1"):
        return self.ns.a7.consolidate(sid, 1, *(chain or self.chain), verdict)

    def _retenido(self, pkg, codigo):
        self.assertFalse(pkg["approved"])
        self.assertEqual(pkg["status"], "HELD_UNVERIFIED_VERDICT")
        self.assertEqual(pkg["checks"], {codigo: False})
        self.assertIsNone(pkg["wav_path"])
        self.assertEqual(pkg["frames"], [])

    def test_veredicto_genuino_aprobado_se_entrega(self):
        pkg = self._consolidar(self.ns.a6.run(self.chain))
        self.assertEqual(pkg["status"], "READY_FOR_DELIVERY")
        self.assertTrue(pkg["approved"])

    def test_alerta_genuina_de_la_vigia_retiene(self):
        wav = self.ns.bus.resolve(self.ns.bus.read(self.chain[4])["payload"]["wav_path"])
        with wav.open("ab") as fh:
            fh.write(b"x")
        pkg = self._consolidar(self.ns.a6.run(self.chain))
        self.assertEqual(pkg["status"], "HELD_BY_VIGIA")
        self.assertFalse(pkg["approved"])
        self.assertFalse(pkg["checks"]["audio_hash_intact"])

    def test_rol_distinto_de_la_vigia_se_rechaza(self):
        v = self._emitir(AntRole.RAZONADORA, SignalType.CONTRACT_VERDICT)
        self._retenido(self._consolidar(v), "verdict_role")

    def test_tipo_no_admitido_se_rechaza(self):
        v = self._emitir(AntRole.VIGIA_CONTRATO, SignalType.SWARM_PACKAGE)
        self._retenido(self._consolidar(v), "verdict_type")

    def test_sesion_distinta_se_rechaza(self):
        v = self._emitir(AntRole.VIGIA_CONTRATO, SignalType.CONTRACT_VERDICT, session_id="otra")
        self._retenido(self._consolidar(v), "verdict_session")

    def test_aprobado_con_tipo_de_alerta_es_inconsistente(self):
        v = self._emitir(AntRole.VIGIA_CONTRATO, SignalType.ALERT, approved=True)
        self._retenido(self._consolidar(v), "verdict_consistency")

    def test_no_aprobado_con_tipo_de_veredicto_es_inconsistente(self):
        v = self._emitir(AntRole.VIGIA_CONTRATO, SignalType.CONTRACT_VERDICT, approved=False)
        self._retenido(self._consolidar(v), "verdict_consistency")

    def test_approved_no_booleano_se_rechaza(self):
        v = self._emitir(AntRole.VIGIA_CONTRATO, SignalType.CONTRACT_VERDICT, approved="si")
        self._retenido(self._consolidar(v), "verdict_consistency")

    def test_veredicto_de_otra_cadena_misma_sesion_se_rechaza(self):
        v_a = self.ns.a6.run(self.chain)
        chain_b = run_until_render(self.ns, "¿Qué es el nodo?", "r1")
        self.assertNotEqual(self._mac_avatar(self.chain), self._mac_avatar(chain_b))
        self._retenido(self._consolidar(v_a, chain=chain_b), "verdict_avatar_binding")

    def test_veredicto_sin_senal_del_avatar_se_rechaza(self):
        v = self._emitir(
            AntRole.VIGIA_CONTRATO, SignalType.CONTRACT_VERDICT, verified_avatar_frame_signal=None
        )
        self._retenido(self._consolidar(v), "verdict_avatar_binding")

    def test_veredicto_inexistente_se_retiene(self):
        pkg = self._consolidar(self.ns.out / "no-existe.lbh")
        self._retenido(pkg, "verdict_readable")

    def test_veredicto_corrupto_se_retiene(self):
        v = self.ns.a6.run(self.chain)
        raw = bytearray(v.read_bytes())
        raw[-1] ^= 0x01
        v.write_bytes(bytes(raw))
        self._retenido(self._consolidar(v), "verdict_readable")

    def test_trama_de_avatar_con_rol_incorrecto_se_rechaza(self):
        v = self.ns.a6.run(self.chain)
        falso_avatar = self.ns.bus.emit(
            AntRole.RAZONADORA, SignalType.AVATAR_FRAME,
            {"session_id": "r1"}, step_tag="falso",
        )
        chain = self.chain[:4] + [falso_avatar]
        self._retenido(self._consolidar(v, chain=chain), "avatar_frame_type")


if __name__ == "__main__":
    unittest.main()
