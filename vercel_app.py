# -*- coding: utf-8 -*-
"""
Entrada Vercel (ASGI): expõe a mesma app FastAPI que `uvicorn simulador_dv.api.main:app`.
Definir `SIMULADOR_PRODUCTION=1` e credenciais Google em produção.
"""
from simulador_dv.api.main import app  # noqa: F401
