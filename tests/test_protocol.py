import unittest

from lbh.protocol import (
    HEADER_SIZE, AntRole, SignalType, decode_lbh_frame, encode_lbh_frame,
)


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.payload = {"a": 1, "texto": "áéñ"}
        self.frame = encode_lbh_frame(AntRole.RAZONADORA, SignalType.STRUCTURED_REPLY, self.payload)

    def test_ida_y_vuelta(self):
        d = decode_lbh_frame(self.frame)
        self.assertEqual(d["role"], AntRole.RAZONADORA)
        self.assertEqual(d["sig_type"], SignalType.STRUCTURED_REPLY)
        self.assertEqual(d["payload"], self.payload)

    def test_cuerpo_alterado_se_rechaza(self):
        raw = bytearray(self.frame)
        raw[HEADER_SIZE] ^= 0x01
        with self.assertRaises(ValueError):
            decode_lbh_frame(bytes(raw))

    def test_cabecera_alterada_se_rechaza(self):
        raw = bytearray(self.frame)
        raw[5] ^= 0x01  # byte del rol
        with self.assertRaises(ValueError):
            decode_lbh_frame(bytes(raw))

    def test_firma_alterada_se_rechaza(self):
        raw = bytearray(self.frame)
        raw[-1] ^= 0x01
        with self.assertRaises(ValueError):
            decode_lbh_frame(bytes(raw))

    def test_trama_truncada_o_con_basura_se_rechaza(self):
        with self.assertRaises(ValueError):
            decode_lbh_frame(self.frame[:-1])
        with self.assertRaises(ValueError):
            decode_lbh_frame(self.frame + b"x")
        with self.assertRaises(ValueError):
            decode_lbh_frame(b"LBH1")

    def test_magic_invalido(self):
        with self.assertRaises(ValueError):
            decode_lbh_frame(b"XXXX" + self.frame[4:])

    def test_tipo_feromona_existe(self):
        self.assertEqual(int(SignalType.KNOWLEDGE_PHEROMONE), 80)


if __name__ == "__main__":
    unittest.main()
