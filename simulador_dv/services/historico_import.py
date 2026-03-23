# -*- coding: utf-8 -*-
"""Reconstrói `dados_cliente` a partir de uma linha de BD Simulações (paridade com sidebar em app.py)."""
from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from simulador_dv.services.cpf_utils import limpar_cpf_visual
from simulador_dv.services.format_utils import safe_float_convert


def fix_cpf_from_row(val: Any) -> str:
    return limpar_cpf_visual(val)


def build_dados_cliente_from_historico_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Espelha o bloco em `app.py` ao carregar histórico (L839–L903).
    `row` usa chaves como na planilha (ex.: 'Nome', 'Renda Part. 1').
    """
    rs = [safe_float_convert(row.get(f"Renda Part. {i}")) for i in range(1, 5)]
    qtd_p = 1
    for i in range(4, 0, -1):
        if rs[i - 1] > 0:
            qtd_p = i
            break
    renda_total = sum(rs)

    soc = str(row.get("Fator Social", "")).strip().lower() in ("sim", "s", "true")
    cot = str(row.get("Cotista FGTS", "")).strip().lower() in ("sim", "s", "true")

    sist_amort = row.get("Sistema de Amortização", "SAC")
    if pd.isnull(sist_amort) or str(sist_amort).strip() == "":
        sist_amort = "SAC"

    def _int_prazo_fin() -> int:
        v = row.get("Prazo Financiamento")
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return 360
        try:
            return int(float(str(v).replace(",", ".")))
        except (TypeError, ValueError):
            return 360

    def _int_ps_parcelas() -> int:
        v = row.get("Número de Parcelas do Pro Soluto", 0)
        try:
            return int(float(str(v).replace(",", ".")))
        except (TypeError, ValueError):
            return 0

    dados: Dict[str, Any] = {
        "nome": row.get("Nome"),
        "cpf": fix_cpf_from_row(row.get("CPF")),
        "data_nascimento": row.get("Data de Nascimento"),
        "qtd_participantes": qtd_p,
        "rendas_lista": rs,
        "renda": renda_total,
        "ranking": row.get("Ranking"),
        "politica": row.get("Política de Pro Soluto"),
        "social": soc,
        "cotista": cot,
        "empreendimento_nome": row.get("Empreendimento Final"),
        "unidade_id": row.get("Unidade Final"),
        "imovel_valor": safe_float_convert(row.get("Preço Unidade Final")),
        "finan_estimado": safe_float_convert(row.get("Financiamento Aprovado")),
        "fgts_sub": safe_float_convert(row.get("Subsídio Máximo")),
        "finan_usado": safe_float_convert(row.get("Financiamento Final")),
        "fgts_sub_usado": safe_float_convert(row.get("FGTS + Subsídio Final")),
        "ps_usado": safe_float_convert(row.get("Pro Soluto Final")),
        "ps_parcelas": _int_ps_parcelas(),
        "ps_mensal": safe_float_convert(row.get("Mensalidade PS")),
        "ato_final": safe_float_convert(row.get("Ato")),
        "ato_30": safe_float_convert(row.get("Ato 30")),
        "ato_60": safe_float_convert(row.get("Ato 60")),
        "ato_90": safe_float_convert(row.get("Ato 90")),
        "prazo_financiamento": _int_prazo_fin(),
        "sistema_amortizacao": sist_amort,
    }
    dados["entrada_total"] = (
        float(dados.get("ato_final", 0) or 0)
        + float(dados.get("ato_30", 0) or 0)
        + float(dados.get("ato_60", 0) or 0)
        + float(dados.get("ato_90", 0) or 0)
    )
    # Referências da curva (útil para ecrãs seguintes)
    dados["finan_f_ref"] = safe_float_convert(row.get("Financiamento Aprovado"))
    dados["sub_f_ref"] = safe_float_convert(row.get("Subsídio Máximo"))
    return dados
