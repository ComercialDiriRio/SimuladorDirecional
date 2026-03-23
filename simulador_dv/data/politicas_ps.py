# -*- coding: utf-8 -*-
"""
Tabela POLITICAS (Excel): colunas A–F usadas no comparador.
A: CLASSIFICAÇÃO | B: PROSOLUTO (% VU) | C: FAIXA RENDA | D/E: FX RENDA 1/2 | F: PARCELAS (máx)

Cada linha (EMCASH, DIAMANTE, OURO, …) alimenta o λ da linha 3 do **bloco** correspondente
no COMPARADOR TX EMCASH (ex.: **K3** Emcash, **X3** Diamante, **AJ3** Ouro): IF(B4 < faixa, FX1, FX2).
O app usa `resolve_politica_row` + `k3_lambda` para reproduzir esse λ por classificação.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

# Valores extraídos de excel_extracao_celulas.txt (aba POLITICAS, linhas 2–7).
# Manter alinhado ao Excel: cada classificação = um bloco do comparador (K3, X3, AJ3…).
DEFAULT_POLITICAS_ROWS: List[Dict[str, Any]] = [
    {"classificacao": "EMCASH", "prosoluto_pct": 0.25, "faixa_renda": 0.0, "fx_renda_1": 0.55, "fx_renda_2": 0.55, "parcelas_max": 66.0},
    {"classificacao": "DIAMANTE", "prosoluto_pct": 0.25, "faixa_renda": 4000.0, "fx_renda_1": 0.5, "fx_renda_2": 0.5, "parcelas_max": 84.0},
    {"classificacao": "OURO", "prosoluto_pct": 0.20, "faixa_renda": 4000.0, "fx_renda_1": 0.5, "fx_renda_2": 0.5, "parcelas_max": 84.0},
    {"classificacao": "PRATA", "prosoluto_pct": 0.18, "faixa_renda": 4000.0, "fx_renda_1": 0.48, "fx_renda_2": 0.48, "parcelas_max": 84.0},
    {"classificacao": "BRONZE", "prosoluto_pct": 0.15, "faixa_renda": 4000.0, "fx_renda_1": 0.45, "fx_renda_2": 0.45, "parcelas_max": 84.0},
    {"classificacao": "AÇO", "prosoluto_pct": 0.12, "faixa_renda": 4000.0, "fx_renda_1": 0.4, "fx_renda_2": 0.4, "parcelas_max": 84.0},
]


@dataclass(frozen=True)
class PoliticaPSRow:
    classificacao: str
    prosoluto_pct: float
    faixa_renda: float
    fx_renda_1: float
    fx_renda_2: float
    parcelas_max: float


def _norm_key(s: str) -> str:
    t = str(s or "").strip().upper()
    if t in ("ACO", "AÇO"):
        return "AÇO"
    return t


def politica_row_from_defaults(classificacao: str) -> Optional[PoliticaPSRow]:
    k = _norm_key(classificacao)
    for row in DEFAULT_POLITICAS_ROWS:
        if _norm_key(str(row["classificacao"])) == k:
            return PoliticaPSRow(
                classificacao=str(row["classificacao"]),
                prosoluto_pct=float(row["prosoluto_pct"]),
                faixa_renda=float(row["faixa_renda"]),
                fx_renda_1=float(row["fx_renda_1"]),
                fx_renda_2=float(row["fx_renda_2"]),
                parcelas_max=float(row["parcelas_max"]),
            )
    return None


def _default_rows_list() -> List[PoliticaPSRow]:
    out = []
    for r in DEFAULT_POLITICAS_ROWS:
        pr = politica_row_from_defaults(r["classificacao"])
        if pr:
            out.append(pr)
    return out


def politicas_from_dataframe(df: Optional[pd.DataFrame]) -> List[PoliticaPSRow]:
    """Interpreta aba POLITICAS com colunas A–F (primeiras 6 colunas se sem nome)."""
    if df is None or df.empty:
        return _default_rows_list()
    out: List[PoliticaPSRow] = []
    df = df.copy()
    cols = list(df.columns)
    for _, row in df.iterrows():
        try:
            vals = [row.get(c) for c in cols[:6]]
            if len(vals) < 6:
                continue
            a, b, c, d, e, f = vals[0], vals[1], vals[2], vals[3], vals[4], vals[5]
            if a is None or str(a).strip() == "" or str(a).lower() == "nan":
                continue
            if "CLASSIF" in str(a).upper():
                continue
            pr = PoliticaPSRow(
                classificacao=str(a).strip(),
                prosoluto_pct=float(b) if b is not None and str(b) != "nan" else 0.0,
                faixa_renda=float(c) if c is not None and str(c) != "nan" else 0.0,
                fx_renda_1=float(d) if d is not None and str(d) != "nan" else 0.0,
                fx_renda_2=float(e) if e is not None and str(e) != "nan" else 0.0,
                parcelas_max=float(f) if f is not None and str(f) != "nan" else 0.0,
            )
            if pr.prosoluto_pct > 0 and pr.parcelas_max > 0:
                out.append(pr)
        except (TypeError, ValueError, IndexError):
            continue
    return out if out else _default_rows_list()


def resolve_politica_row(
    politica_ui: str,
    ranking: str,
    df_politicas: Optional[pd.DataFrame] = None,
) -> PoliticaPSRow:
    """
    - Política Emcash (produto) → linha EMCASH na POLITICAS.
    - Política Direcional → linha do ranking (DIAMANTE, OURO, ...).
    """
    rows = politicas_from_dataframe(df_politicas)

    if str(politica_ui or "").strip().lower() == "emcash":
        key = "EMCASH"
    else:
        key = _norm_key(ranking or "DIAMANTE")

    for r in rows:
        if _norm_key(r.classificacao) == key:
            return r
    fb = politica_row_from_defaults(key)
    if fb:
        return fb
    return rows[0]


def classificacao_efetiva(politica_ui: str, ranking: str) -> str:
    if str(politica_ui or "").strip().lower() == "emcash":
        return "EMCASH"
    return _norm_key(ranking or "DIAMANTE")


def bd_ranking_to_politicas_dataframe(df_rank: Optional[pd.DataFrame]) -> pd.DataFrame:
    """
    Converte aba «BD Ranking» (CLASSIFICAÇÃO, PROSOLUTO %, FAIXA RENDA, FX RENDA 1/2, PARCELAS)
    para o formato esperado por `politicas_from_dataframe` (6 colunas posicionais A–F).
    """
    if df_rank is None or df_rank.empty:
        return pd.DataFrame()
    df = df_rank.copy()
    df.columns = [str(c).strip() for c in df.columns]
    col_cls = "CLASSIFICAÇÃO" if "CLASSIFICAÇÃO" in df.columns else None
    if not col_cls and "CLASSIFICACAO" in df.columns:
        col_cls = "CLASSIFICACAO"
    if not col_cls:
        return pd.DataFrame()

    def _pct(v: Any) -> float:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return 0.0
        s = str(v).strip().replace("%", "").replace(",", ".")
        try:
            x = float(s)
        except ValueError:
            return 0.0
        return x / 100.0 if x > 1.0 else x

    def _fnum(v: Any) -> float:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return 0.0
        s = str(v).strip().replace("%", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return 0.0

    rows_out: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        cls = r.get(col_cls)
        if cls is None or str(cls).strip() == "" or str(cls).upper().startswith("CLASS"):
            continue
        rows_out.append(
            {
                "A": str(cls).strip(),
                "B": _pct(r.get("PROSOLUTO")),
                "C": _fnum(r.get("FAIXA RENDA")),
                "D": _fnum(r.get("FX RENDA 1")),
                "E": _fnum(r.get("FX RENDA 2")),
                "F": _fnum(r.get("PARCELAS")),
            }
        )
    if not rows_out:
        return pd.DataFrame()
    return pd.DataFrame(rows_out)
