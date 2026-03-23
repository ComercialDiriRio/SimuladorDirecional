# -*- coding: utf-8 -*-
import unittest

from simulador_dv.services.historico_import import build_dados_cliente_from_historico_row


class TestHistoricoImport(unittest.TestCase):
    def test_reconstrucao_renda_e_atos(self):
        row = {
            "Nome": "Teste",
            "CPF": "12345678901",
            "Renda Part. 1": 3000,
            "Renda Part. 2": 2000,
            "Renda Part. 3": 0,
            "Renda Part. 4": 0,
            "Fator Social": "Sim",
            "Cotista FGTS": "Não",
            "Ranking": "DIAMANTE",
            "Política de Pro Soluto": "Direcional",
            "Empreendimento Final": "Emp X",
            "Unidade Final": "A-1",
            "Preço Unidade Final": 400000,
            "Financiamento Final": 200000,
            "FGTS + Subsídio Final": 10000,
            "Pro Soluto Final": 15000,
            "Número de Parcelas do Pro Soluto": 48,
            "Mensalidade PS": 500,
            "Ato": 1000,
            "Ato 30": 500,
            "Ato 60": 500,
            "Ato 90": 0,
            "Prazo Financiamento": 360,
            "Sistema de Amortização": "SAC",
            "Financiamento Aprovado": 250000,
            "Subsídio Máximo": 12000,
        }
        d = build_dados_cliente_from_historico_row(row)
        self.assertEqual(d["renda"], 5000.0)
        self.assertEqual(d["qtd_participantes"], 2)
        self.assertEqual(d["entrada_total"], 2000.0)
        self.assertTrue(d["social"])


if __name__ == "__main__":
    unittest.main()
