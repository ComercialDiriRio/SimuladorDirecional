# -*- coding: utf-8 -*-
import os
import unittest

from fastapi.testclient import TestClient

from simulador_dv.api.main import app
from simulador_dv.api.session_store import SESSION_COOKIE_NAME


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("status"), "ok")

    def test_premissas_default(self):
        r = self.client.get("/api/premissas/default")
        self.assertEqual(r.status_code, 200)
        self.assertIn("emcash_fin_m", r.json())

    def test_metricas_pro_soluto(self):
        r = self.client.post(
            "/api/pro-soluto/metricas",
            json={
                "renda": 5000.0,
                "valor_unidade": 400000.0,
                "politica_ui": "Direcional",
                "ranking": "DIAMANTE",
                "premissas": None,
                "ps_cap_estoque": None,
            },
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("parcela_max_g14", data)
        self.assertIn("ps_max_efetivo", data)

    def test_auth_demo(self):
        os.environ["SIMULADOR_API_DEMO"] = "1"
        try:
            r = self.client.post(
                "/api/auth/login",
                json={"email": "demo@direcional.local", "password": "demo"},
            )
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.json().get("ok"))
        finally:
            os.environ.pop("SIMULADOR_API_DEMO", None)

    def test_session_create_and_get(self):
        c = TestClient(app)
        r = c.post("/api/session", json={})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("session_id", data)
        self.assertIn(SESSION_COOKIE_NAME, c.cookies)
        r2 = c.get("/api/session")
        self.assertEqual(r2.status_code, 200)
        body = r2.json()
        self.assertEqual(body.get("passo_simulacao"), "input")
        self.assertIn("cliente_ativo", body)
        self.assertFalse(body.get("cliente_ativo"))
        self.assertIn("session_ui", body)

    def test_login_demo_session_email(self):
        os.environ["SIMULADOR_API_DEMO"] = "1"
        try:
            c = TestClient(app)
            r = c.post(
                "/api/auth/login",
                json={"email": "demo@direcional.local", "password": "demo"},
            )
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.json().get("ok"))
            self.assertIn("session_id", r.json())
            r2 = c.get("/api/session")
            self.assertEqual(r2.json().get("email"), "demo@direcional.local")
        finally:
            os.environ.pop("SIMULADOR_API_DEMO", None)

    def test_put_cliente(self):
        c = TestClient(app)
        c.post("/api/session", json={})
        r = c.put("/api/cliente", json={"nome": "Cliente Teste", "renda": 4500.0})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["dados_cliente"].get("nome"), "Cliente Teste")

    def test_recomendacoes_endpoint(self):
        c = TestClient(app)
        c.post("/api/session", json={})
        r = c.post("/api/simulacao/recomendacoes", json={})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("ideal", body)
        self.assertIn("seguro", body)
        self.assertIn("facilitado", body)

    def test_cadastros_buscar_requires_session(self):
        c = TestClient(app)
        r = c.get("/api/cadastros/buscar")
        self.assertEqual(r.status_code, 401)

    def test_selection_termometro_requires_params(self):
        c = TestClient(app)
        c.post("/api/session", json={})
        r = c.get("/api/selection/termometro")
        self.assertIn(r.status_code, (400, 422))

    def test_salvar_simulacao_sem_credenciais_sheets(self):
        """Sem Google creds, append falha com 503 (esperado em CI)."""
        c = TestClient(app)
        c.post("/api/session", json={})
        c.put(
            "/api/cliente",
            json={
                "nome": "X",
                "renda": 5000.0,
            },
        )
        r = c.post("/api/salvar-simulacao")
        self.assertIn(r.status_code, (503, 200))

    def test_pagamento_simular(self):
        c = TestClient(app)
        c.post("/api/session", json={})
        r = c.post(
            "/api/pagamento/simular",
            json={
                "valor_financiado": 300000.0,
                "meses_fin": 360,
                "taxa_anual": 10.5,
                "sistema": "SAC",
                "ps_mensal": 0.0,
                "meses_ps": 0,
                "ato_final": 5000.0,
                "ato_30": 0.0,
                "ato_60": 0.0,
                "ato_90": 0.0,
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("fluxo", r.json())


if __name__ == "__main__":
    unittest.main()
