# -*- coding: utf-8 -*-
"""
Servidor FastAPI: API JSON em `/api/*` e ficheiros estáticos do front em `/static/*`.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from simulador_dv.api.routers import (
    analytics,
    auth,
    cadastros,
    cliente,
    conteudo,
    estoque,
    fechamento,
    galeria,
    health,
    home_content,
    pagamento,
    premissas,
    pro_soluto,
    recomendacoes,
    resumo,
    selection,
    session_routes,
)

logging.basicConfig(
    level=logging.INFO,
    format="[SIMULADOR] %(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("simulador_dv.api")

ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "web"

app = FastAPI(
    title="Simulador Direcional DV",
    description="API REST para a UI web (HTML/CSS/JS). Ver `simulador_dv/api/INVENTORY.md`.",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        logger.exception("[%s %s] 500 | %.0fms | Erro não tratado", request.method, request.url.path, elapsed)
        return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor"})
    elapsed = (time.perf_counter() - start) * 1000
    status = response.status_code
    if status >= 500:
        logger.error("[%s %s] %d | %.0fms", request.method, request.url.path, status, elapsed)
    elif status >= 400:
        logger.warning("[%s %s] %d | %.0fms", request.method, request.url.path, status, elapsed)
    else:
        if not request.url.path.startswith("/static"):
            logger.info("[%s %s] %d | %.0fms", request.method, request.url.path, status, elapsed)
    return response


@app.middleware("http")
async def static_asset_cache_headers(request: Request, call_next):
    """Cache longo para JS/CSS/imagens em /static/ (login mais leve em visitas repetidas)."""
    response = await call_next(request)
    p = request.url.path or ""
    if p.startswith("/static/"):
        pl = p.lower()
        if pl.endswith(
            (".js", ".mjs", ".css", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".svg", ".woff2")
        ):
            response.headers["Cache-Control"] = "public, max-age=604800"
    return response


@app.on_event("startup")
async def _on_startup():
    try:
        from simulador_dv.services.simulacao_sheets import ensure_bd_simulacoes_header

        ensure_bd_simulacoes_header()
        logger.info("Startup: header BD Simulações verificado (cache do sistema mantido para cold start)")
    except Exception:
        logger.exception("Falha ao inicializar header BD Simulações")

app.include_router(health.router, prefix="/api")
app.include_router(premissas.router, prefix="/api")
app.include_router(pro_soluto.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(session_routes.router, prefix="/api")
app.include_router(cliente.router, prefix="/api")
app.include_router(cadastros.router, prefix="/api")
app.include_router(fechamento.router, prefix="/api")
app.include_router(recomendacoes.router, prefix="/api")
app.include_router(estoque.router, prefix="/api")
app.include_router(selection.router, prefix="/api")
app.include_router(pagamento.router, prefix="/api")
app.include_router(resumo.router, prefix="/api")
app.include_router(galeria.router, prefix="/api")
app.include_router(home_content.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(conteudo.router, prefix="/api")
if WEB_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
async def serve_index():
    """Serve a SPA/HTML principal."""
    index = WEB_DIR / "index.html"
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
    return {"detail": "Front-end não encontrado. Crie a pasta web/ (ver README)."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "simulador_dv.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
