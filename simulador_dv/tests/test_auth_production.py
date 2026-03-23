# -*- coding: utf-8 -*-
import os
import unittest

from fastapi.testclient import TestClient

from simulador_dv.api.main import app


class TestAuthProduction(unittest.TestCase):
    def test_demo_bloqueado_em_producao(self):
        os.environ["SIMULADOR_PRODUCTION"] = "1"
        os.environ["SIMULADOR_API_DEMO"] = "1"
        try:
            c = TestClient(app)
            r = c.post(
                "/api/auth/login",
                json={"email": "demo@direcional.local", "password": "demo"},
            )
            self.assertNotEqual(r.status_code, 200)
        finally:
            os.environ.pop("SIMULADOR_PRODUCTION", None)
            os.environ.pop("SIMULADOR_API_DEMO", None)


if __name__ == "__main__":
    unittest.main()
