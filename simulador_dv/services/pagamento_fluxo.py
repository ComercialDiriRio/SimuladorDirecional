# -*- coding: utf-8 -*-
"""Projeção de fluxo de pagamento (espelho de app.py, sem Streamlit)."""
from __future__ import annotations

from typing import Any, Dict

import pandas as pd


def calcular_fluxo_pagamento_detalhado(
    valor_fin: float,
    meses_fin: int,
    taxa_anual: float,
    sistema: str,
    ps_mensal: float,
    meses_ps: int,
    atos_dict: Dict[str, Any],
) -> pd.DataFrame:
    i_mensal = (1 + taxa_anual / 100) ** (1 / 12) - 1
    fluxo = []
    saldo_devedor = valor_fin
    amortizacao_sac = valor_fin / meses_fin if meses_fin > 0 else 0

    pmt_price = 0.0
    if sistema == "PRICE" and meses_fin > 0:
        pmt_price = valor_fin * (i_mensal * (1 + i_mensal) ** meses_fin) / ((1 + i_mensal) ** meses_fin - 1)

    order_map = {"Financiamento": 1, "Pro Soluto": 2, "Entrada/Ato": 3}

    for m in range(1, meses_fin + 1):
        if sistema == "SAC":
            juros = saldo_devedor * i_mensal
            parc_fin = amortizacao_sac + juros
            saldo_devedor -= amortizacao_sac
        else:
            parc_fin = pmt_price
            juros = saldo_devedor * i_mensal
            amort = pmt_price - juros
            saldo_devedor -= amort

        parc_ps = ps_mensal if m <= meses_ps else 0

        val_ato = 0.0
        if m == 1:
            val_ato = float(atos_dict.get("ato_final", 0.0) or 0)
        elif m == 2:
            val_ato = float(atos_dict.get("ato_30", 0.0) or 0)
        elif m == 3:
            val_ato = float(atos_dict.get("ato_60", 0.0) or 0)
        elif m == 4:
            val_ato = float(atos_dict.get("ato_90", 0.0) or 0)

        fluxo.append(
            {
                "Mês": int(m),
                "Valor": float(parc_fin),
                "Tipo": "Financiamento",
                "Ordem_Tipo": order_map["Financiamento"],
                "Total": float(parc_fin + parc_ps + val_ato),
            }
        )

        if parc_ps > 0:
            fluxo.append(
                {
                    "Mês": int(m),
                    "Valor": float(parc_ps),
                    "Tipo": "Pro Soluto",
                    "Ordem_Tipo": order_map["Pro Soluto"],
                    "Total": float(parc_fin + parc_ps + val_ato),
                }
            )

        if val_ato > 0:
            fluxo.append(
                {
                    "Mês": int(m),
                    "Valor": float(val_ato),
                    "Tipo": "Entrada/Ato",
                    "Ordem_Tipo": order_map["Entrada/Ato"],
                    "Total": float(parc_fin + parc_ps + val_ato),
                }
            )

    return pd.DataFrame(fluxo)
