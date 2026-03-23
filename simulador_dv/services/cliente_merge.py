# -*- coding: utf-8 -*-
"""Merge BD Clientes + última linha em BD Simulações (mesmo CPF)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from simulador_dv.services.cpf_utils import limpar_cpf_visual
from simulador_dv.services.format_utils import safe_float_convert
from simulador_dv.services.historico_import import build_dados_cliente_from_historico_row


def _truthy_pt(val: Any) -> bool:
    s = str(val or "").strip().lower()
    return s in ("sim", "s", "true", "1", "yes")


def build_dados_cliente_from_clientes_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Mapeia linha da aba BD Clientes para chaves internas `dados_cliente`."""
    nome = row.get("Nome") or row.get("nome")
    cpf_raw = row.get("CPF") or row.get("cpf")
    cpf = limpar_cpf_visual(cpf_raw)

    qtd = 1
    for qkey in ("QTD. Participantes", "QTD. Particiipantes", "Qtd Participantes"):
        if qkey in row and row[qkey] is not None and str(row[qkey]).strip() != "":
            try:
                qtd = max(1, min(4, int(float(str(row[qkey]).replace(",", ".")))))
            except (TypeError, ValueError):
                qtd = 1
            break

    rs: List[float] = []
    for i in range(1, 5):
        v = row.get(f"Renda {i}") or row.get(f"Renda Part. {i}") or row.get(f"Renda Part {i}")
        rs.append(safe_float_convert(v))
    while len(rs) < 4:
        rs.append(0.0)
    renda_total = sum(rs[:qtd])

    ranking = row.get("Ranking") or row.get("ranking") or "DIAMANTE"
    politica = row.get("Política de Pro Soluto") or row.get("Politica de Pro Soluto") or "Direcional"
    cotista = _truthy_pt(row.get("Cotista") or row.get("Cotista FGTS") or "")
    social = _truthy_pt(row.get("Fator Social") or row.get("fator social") or "")

    prazo_ps_max = 66 if "emcash" in str(politica).lower() else 84

    return {
        "nome": str(nome or "").strip(),
        "cpf": cpf,
        "data_nascimento": row.get("Data de Nascimento") or row.get("Data Nascimento"),
        "qtd_participantes": qtd,
        "rendas_lista": rs,
        "renda": renda_total,
        "ranking": str(ranking).strip().upper() if ranking else "DIAMANTE",
        "politica": str(politica).strip(),
        "social": social,
        "cotista": cotista,
        "prazo_ps_max": prazo_ps_max,
        "limit_ps_renda": 0.30,
        "finan_usado_historico": 0.0,
        "ps_usado_historico": 0.0,
        "fgts_usado_historico": 0.0,
    }


def _parse_br_datetime(val: Any) -> float:
    """Timestamp para ordenar 'última' simulação."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return 0.0
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return 0.0
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(s[: len(fmt) + 10], fmt).timestamp()
        except ValueError:
            continue
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).timestamp()
        except ValueError:
            pass
    return 0.0


def find_last_simulation_row_for_cpf(df_sim: pd.DataFrame, cpf: str) -> Optional[Dict[str, Any]]:
    if df_sim is None or df_sim.empty or "CPF" not in df_sim.columns:
        return None
    cpf_n = limpar_cpf_visual(cpf)
    df = df_sim.copy()
    df["_cpf_n"] = df["CPF"].apply(limpar_cpf_visual)
    sub = df[df["_cpf_n"] == cpf_n]
    if sub.empty:
        return None
    date_col = None
    for c in ("Data/Horário", "Data/Horario", "Carimbo de data/hora", "Data Horário"):
        if c in sub.columns:
            date_col = c
            break
    if date_col:
        sub = sub.copy()
        sub["_ts"] = sub[date_col].apply(_parse_br_datetime)
        sub = sub.sort_values("_ts", ascending=False)
    else:
        sub = sub.iloc[[-1]]
    row = sub.iloc[0]
    return row.astype(object).where(pd.notnull(row), None).to_dict()


# Preservar identidade a partir de BD Clientes; restante vem da última simulação quando existir.
_IDENTITY_KEYS = frozenset({"nome", "cpf", "data_nascimento"})


def merge_cliente_base_com_ultima_simulacao(
    row_cliente: Dict[str, Any],
    df_simulacoes: pd.DataFrame,
) -> Dict[str, Any]:
    base = build_dados_cliente_from_clientes_row(row_cliente)
    last = find_last_simulation_row_for_cpf(df_simulacoes, base.get("cpf", ""))
    if not last:
        return base
    full_sim = build_dados_cliente_from_historico_row(last)
    out = dict(base)
    for k, v in full_sim.items():
        if k in _IDENTITY_KEYS:
            continue
        if v is None:
            continue
        if isinstance(v, float) and pd.isna(v):
            continue
        out[k] = v
    return out
