# -*- coding: utf-8 -*-
from fastapi import APIRouter

from simulador_dv.api.schemas import (
    MetricasProSolutoIn,
    MetricasProSolutoOut,
    politica_row_to_out,
)
from simulador_dv.core.pro_soluto_comparador import metricas_pro_soluto

router = APIRouter(tags=["pro-soluto"])


@router.post("/pro-soluto/metricas", response_model=MetricasProSolutoOut)
def post_metricas_pro_soluto(body: MetricasProSolutoIn) -> MetricasProSolutoOut:
    m = metricas_pro_soluto(
        renda=body.renda,
        valor_unidade=body.valor_unidade,
        politica_ui=body.politica_ui,
        ranking=body.ranking,
        premissas=body.premissas,
        df_politicas=None,
        ps_cap_estoque=body.ps_cap_estoque,
    )
    row = m["politica_row"]
    return MetricasProSolutoOut(
        k3=float(m["k3"]),
        e1=float(m["e1"]),
        parcela_max_j8=float(m["parcela_max_j8"]),
        parcela_max_g14=float(m["parcela_max_g14"]),
        pv_l8=float(m["pv_l8"]),
        cap_valor_unidade=float(m["cap_valor_unidade"]),
        ps_max_comparador_politica=float(m["ps_max_comparador_politica"]),
        ps_max_efetivo=float(m["ps_max_efetivo"]),
        prazo_ps_politica=int(m["prazo_ps_politica"]),
        politica_row=politica_row_to_out(row),
    )
