# -*- coding: utf-8 -*-
"""Distribuição do saldo restante em atos 30/60/90 (paridade payment_flow)."""
from __future__ import annotations

from typing import Any, Dict


def distribuir_restante_atos(
    dados_cliente: Dict[str, Any],
    n_parcelas: int,
) -> Dict[str, Any]:
    """
    Espelha `distribuir_restante` em app.py (atos após imediato).
    n_parcelas: 2 → 30/60; 3 → 30/60/90 (Emcash desabilita 3 no Streamlit).
    """
    d = dict(dados_cliente or {})
    u_valor = float(d.get("imovel_valor", 0) or 0)
    f_u = float(d.get("finan_usado", 0) or 0)
    fgts_u = float(d.get("fgts_sub_usado", 0) or 0)
    ps_atual = float(d.get("ps_usado", 0) or 0)
    a1 = float(d.get("ato_final", 0) or 0)

    gap_total = max(0.0, u_valor - f_u - fgts_u - ps_atual)
    restante = max(0.0, gap_total - a1)
    n = int(n_parcelas)
    if n not in (2, 3):
        n = 2

    if restante > 0 and n > 0:
        val_per = restante / n
        if n == 2:
            d["ato_30"] = float(val_per)
            d["ato_60"] = float(val_per)
            d["ato_90"] = 0.0
        else:
            d["ato_30"] = float(val_per)
            d["ato_60"] = float(val_per)
            d["ato_90"] = float(val_per)
    else:
        d["ato_30"] = 0.0
        d["ato_60"] = 0.0
        d["ato_90"] = 0.0

    return d
