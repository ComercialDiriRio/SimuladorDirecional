# -*- coding: utf-8 -*-
import unittest

from simulador_dv.services.simulacao_sheets import build_nova_linha_simulacao


class TestNovaLinhaSheets(unittest.TestCase):
    def test_poder_aquisicao_medio_matches_streamlit_formula(self):
        d = {
            "nome": "Teste",
            "cpf": "123",
            "data_nascimento": "01/01/1990",
            "rendas_lista": [3000.0, 2000.0, 0.0, 0.0],
            "renda": 5000.0,
            "finan_f_ref": 100000.0,
            "sub_f_ref": 50000.0,
            "imovel_valor": 400000.0,
            "entrada_total": 10000.0,
            "ps_usado": 20000.0,
            "finan_usado": 250000.0,
            "fgts_sub_usado": 30000.0,
            "ps_parcelas": 48,
            "ps_mensal": 500.0,
            "prazo_financiamento": 360,
            "sistema_amortizacao": "SAC",
            "ranking": "DIAMANTE",
            "politica": "Direcional",
            "social": True,
            "cotista": True,
            "empreendimento_nome": "Emp X",
            "unidade_id": "A-101",
            "ato_final": 5000.0,
            "ato_30": 1000.0,
            "ato_60": 1000.0,
            "ato_90": 1000.0,
        }
        row = build_nova_linha_simulacao(d, user_name="Corretor", user_imobiliaria="Canal", volta_caixa=1500.0)
        esperado_pam = (2 * 5000.0) + 100000.0 + 50000.0 + (400000.0 * 0.10)
        self.assertAlmostEqual(row["Poder de Aquisição Médio"], esperado_pam, places=4)
        self.assertAlmostEqual(row["Capacidade de Entrada"], 30000.0, places=4)
        self.assertEqual(row["Volta ao Caixa"], 1500.0)
        self.assertEqual(row["Nome do Corretor"], "Corretor")
        self.assertEqual(row["Canal/Imobiliária"], "Canal")


if __name__ == "__main__":
    unittest.main()
