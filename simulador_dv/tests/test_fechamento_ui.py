# -*- coding: utf-8 -*-
import unittest

from simulador_dv.services.fechamento_ui import aplicar_defaults_fechamento


class TestFechamentoDefaults(unittest.TestCase):
    def test_preenche_finan_fgts_quando_zero(self):
        d = {"renda": 5000.0, "finan_usado": 0.0, "fgts_sub_usado": 0.0}
        out = aplicar_defaults_fechamento(d, 100000.0, 50000.0)
        self.assertEqual(out["finan_usado"], 100000.0)
        self.assertEqual(out["fgts_sub_usado"], 50000.0)
        self.assertEqual(out["finan_f_ref"], 100000.0)

    def test_preserva_finan_quando_nao_zero(self):
        d = {"renda": 5000.0, "finan_usado": 80000.0, "fgts_sub_usado": 0.0}
        out = aplicar_defaults_fechamento(d, 100000.0, 50000.0)
        self.assertEqual(out["finan_usado"], 80000.0)


if __name__ == "__main__":
    unittest.main()
