# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MetricasProSolutoIn(BaseModel):
    renda: float = Field(..., ge=0)
    valor_unidade: float = Field(..., ge=0)
    politica_ui: str = "Direcional"
    ranking: str = "DIAMANTE"
    premissas: Optional[Dict[str, float]] = None
    ps_cap_estoque: Optional[float] = Field(None, ge=0)


class PoliticaRowOut(BaseModel):
    classificacao: str
    prosoluto_pct: float
    faixa_renda: float
    fx_renda_1: float
    fx_renda_2: float
    parcelas_max: float


class MetricasProSolutoOut(BaseModel):
    k3: float
    e1: float
    parcela_max_j8: float
    parcela_max_g14: float
    pv_l8: float
    cap_valor_unidade: float
    ps_max_comparador_politica: float
    ps_max_efetivo: float
    prazo_ps_politica: int
    politica_row: PoliticaRowOut


class LoginIn(BaseModel):
    email: str
    password: str


class LoginOut(BaseModel):
    ok: bool
    message: str = ""
    session_id: Optional[str] = None


class HealthOut(BaseModel):
    status: str = "ok"
    service: str = "simulador-dv-api"


def politica_row_to_out(row: Any) -> PoliticaRowOut:
    return PoliticaRowOut(
        classificacao=str(row.classificacao),
        prosoluto_pct=float(row.prosoluto_pct),
        faixa_renda=float(row.faixa_renda),
        fx_renda_1=float(row.fx_renda_1),
        fx_renda_2=float(row.fx_renda_2),
        parcelas_max=float(row.parcelas_max),
    )
