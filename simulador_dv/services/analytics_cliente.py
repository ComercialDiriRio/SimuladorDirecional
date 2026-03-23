# -*- coding: utf-8 -*-
"""Payload para o painel `client_analytics` (dados para gráficos no browser)."""
from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from simulador_dv.core.comparador_emcash import resolver_taxa_financiamento_anual_pct
from simulador_dv.data.premissas import DEFAULT_PREMISSAS
from simulador_dv.services.pagamento_fluxo import calcular_fluxo_pagamento_detalhado


def build_analytics_payload(
    dados_cliente: Dict[str, Any],
    premissas_dict: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    d = dict(dados_cliente or {})
    _prem = dict(DEFAULT_PREMISSAS)
    if premissas_dict:
        _prem.update(premissas_dict)

    def taxa_fin_vigente() -> float:
        return float(resolver_taxa_financiamento_anual_pct(d, _prem))

    labels_compra = ["Ato", "30 Dias", "60 Dias", "90 Dias", "Pro Soluto", "Financiamento", "FGTS/Subsídio"]
    values_compra = [
        float(d.get("ato_final", 0) or 0),
        float(d.get("ato_30", 0) or 0),
        float(d.get("ato_60", 0) or 0),
        float(d.get("ato_90", 0) or 0),
        float(d.get("ps_usado", 0) or 0),
        float(d.get("finan_usado", 0) or 0),
        float(d.get("fgts_sub_usado", 0) or 0),
    ]
    composicao_compra = [{"tipo": l, "valor": v} for l, v in zip(labels_compra, values_compra) if v > 0]

    rendas = d.get("rendas_lista") or []
    composicao_renda = [{"participante": f"Part. {i + 1}", "renda": float(r)} for i, r in enumerate(rendas) if float(r or 0) > 0]

    v_fin = float(d.get("finan_usado", 0) or 0)
    p_fin = int(d.get("prazo_financiamento", 360) or 360)
    p_ps = int(d.get("ps_parcelas", 0) or 0)
    v_ps_mensal = float(d.get("ps_mensal", 0) or 0)
    sist = str(d.get("sistema_amortizacao", "SAC") or "SAC")
    atos_dict = {
        "ato_final": float(d.get("ato_final", 0) or 0),
        "ato_30": float(d.get("ato_30", 0) or 0),
        "ato_60": float(d.get("ato_60", 0) or 0),
        "ato_90": float(d.get("ato_90", 0) or 0),
    }

    fluxo_mensal: List[Dict[str, Any]] = []
    if v_fin > 0 and p_fin > 0:
        df_fluxo = calcular_fluxo_pagamento_detalhado(
            v_fin,
            p_fin,
            taxa_fin_vigente(),
            sist,
            v_ps_mensal,
            p_ps,
            atos_dict,
        )
        if not df_fluxo.empty and "Mês" in df_fluxo.columns and "Tipo" in df_fluxo.columns:
            fin_col, ps_col, ato_col = "Financiamento", "Pro Soluto", "Entrada/Ato"
            pivot = df_fluxo.groupby(["Mês", "Tipo"])["Valor"].sum().unstack(fill_value=0.0)
            for col in (fin_col, ps_col, ato_col):
                if col not in pivot.columns:
                    pivot[col] = 0.0
            fluxo_mensal = []
            for mes in sorted(pivot.index.astype(int)):
                row = pivot.loc[mes]
                fv = float(row[fin_col])
                pv = float(row[ps_col])
                av = float(row[ato_col])
                fluxo_mensal.append(
                    {
                        "Mês": int(mes),
                        "financiamento": fv,
                        "pro_soluto": pv,
                        "atos": av,
                        "Total": fv + pv + av,
                    }
                )
        else:
            fluxo_mensal = []

    mes_fim_atos = 0
    if float(d.get("ato_90", 0) or 0) > 0:
        mes_fim_atos = 4
    elif float(d.get("ato_60", 0) or 0) > 0:
        mes_fim_atos = 3
    elif float(d.get("ato_30", 0) or 0) > 0:
        mes_fim_atos = 2
    elif float(d.get("ato_final", 0) or 0) > 0:
        mes_fim_atos = 1

    mes_fim_ps = int(p_ps) if v_ps_mensal > 0 and p_ps > 0 else 0

    return {
        "dados_cliente": d,
        "composicao_compra": composicao_compra,
        "composicao_renda": composicao_renda,
        "fluxo_mensal": fluxo_mensal,
        "marcadores": {
            "mes_fim_atos": mes_fim_atos,
            "mes_fim_ps": mes_fim_ps,
        },
    }
