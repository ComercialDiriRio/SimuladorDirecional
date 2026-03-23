# -*- coding: utf-8 -*-
import unittest

from simulador_dv.core.pro_soluto_comparador import (
    fator_renda_liquido,
    k3_lambda,
    metricas_pro_soluto,
    parcela_max_g14,
    parcela_ps_pmt,
    pv_l8_positivo,
)
from simulador_dv.data.politicas_ps import politica_row_from_defaults
from simulador_dv.data.premissas import DEFAULT_PREMISSAS


class TestProSoluto(unittest.TestCase):
    def test_k3_emcash(self):
        row = politica_row_from_defaults("EMCASH")
        self.assertIsNotNone(row)
        k3 = k3_lambda(5000.0, row)
        self.assertEqual(k3, 0.55)
        self.assertAlmostEqual(fator_renda_liquido(k3), 0.25)

    def test_parcela_g14(self):
        row = politica_row_from_defaults("EMCASH")
        self.assertIsNotNone(row)
        k3 = k3_lambda(3700.0, row)
        g14 = parcela_max_g14(3700.0, k3)
        self.assertAlmostEqual(g14, 3700.0 * 0.25)

    def test_parcela_ps_pmt_positive(self):
        p = parcela_ps_pmt(38412.0, 84, None, "Emcash")
        self.assertGreater(p, 0)
        self.assertAlmostEqual(p, 676.87, places=1)

    def test_parcela_ps_pmt_calibracao_i5_emcash_84x(self):
        """I5 do comparador: E2 = PREMISSAS B4 (emcash_fin_m), independente da política na UI."""
        cases = [
            (25000.0, 440.53),
            (30000.0, 528.64),
            (35000.0, 616.74),
            (39663.0, 698.91),
        ]
        for pv, esperado in cases:
            got = parcela_ps_pmt(pv, 84, DEFAULT_PREMISSAS, "Direcional")
            self.assertAlmostEqual(got, esperado, places=2)

    def test_parcela_ps_pmt_mesmo_e2_emcash_e_direcional(self):
        """Direcional e Emcash na UI devem gerar a mesma mensalidade PS (I5)."""
        p = parcela_ps_pmt(35000.0, 84, DEFAULT_PREMISSAS, "Emcash")
        q = parcela_ps_pmt(35000.0, 84, DEFAULT_PREMISSAS, "Direcional")
        self.assertAlmostEqual(p, q, places=6)

    def test_pv_l8_positive(self):
        l8 = pv_l8_positivo(0.0089, 66, 500.0)
        self.assertGreater(l8, 0)

    def test_metricas_keys(self):
        m = metricas_pro_soluto(
            renda=3700.0,
            valor_unidade=500_000.0,
            politica_ui="Emcash",
            ranking="DIAMANTE",
            premissas=None,
            df_politicas=None,
            ps_cap_estoque=80_000.0,
        )
        self.assertIn("ps_max_efetivo", m)
        self.assertIn("parcela_max_j8", m)

    def test_g14_tier_diamante_vs_emcash_lambda(self):
        """λ (K3 vs X3) muda com a linha POLITICAS da classificação efetiva."""
        m_em = metricas_pro_soluto(
            renda=5000.0,
            valor_unidade=400_000.0,
            politica_ui="Emcash",
            ranking="DIAMANTE",
            premissas=None,
            df_politicas=None,
            ps_cap_estoque=None,
        )
        m_di = metricas_pro_soluto(
            renda=5000.0,
            valor_unidade=400_000.0,
            politica_ui="Direcional",
            ranking="DIAMANTE",
            premissas=None,
            df_politicas=None,
            ps_cap_estoque=None,
        )
        self.assertAlmostEqual(m_em["k3"], 0.55)
        self.assertAlmostEqual(m_di["k3"], 0.5)
        self.assertGreater(m_em["parcela_max_g14"], m_di["parcela_max_g14"])


if __name__ == "__main__":
    unittest.main()
