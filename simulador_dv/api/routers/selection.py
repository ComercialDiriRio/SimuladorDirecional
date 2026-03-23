# -*- coding: utf-8 -*-
"""Termómetro e contexto da etapa `selection` (Streamlit)."""
from __future__ import annotations

from typing import Annotated, Any, Dict, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from simulador_dv.api.data_context import get_simulador_context
from simulador_dv.api.deps import require_session_state
from simulador_dv.services.pagamento_ui import termometro_selection
from simulador_dv.services.sistema_data import load_sistema_dataframes

router = APIRouter(prefix="/selection", tags=["selection"])


@router.get("/termometro")
def get_termometro(
    st: Annotated[dict, Depends(require_session_state)],
    empreendimento: str = Query(...),
    identificador: str = Query(...),
    valor_final: Optional[float] = Query(None, description="Valor final de venda (opcional)"),
) -> Dict[str, Any]:
    motor, _, _, _, _, _ = get_simulador_context()
    _, df_estoque, _, _, _, _, _ = load_sistema_dataframes()
    d = st.get("dados_cliente") or {}
    row = df_estoque[
        (df_estoque["Identificador"].astype(str) == str(identificador))
        & (df_estoque["Empreendimento"].astype(str).str.strip() == empreendimento.strip())
    ]
    if row.empty:
        raise HTTPException(status_code=404, detail="Unidade não encontrada no estoque")
    u_row = row.iloc[0]
    v_venda = float(u_row.get("Valor de Venda", 0) or 0)
    valor_para_termo = float(valor_final) if valor_final is not None and valor_final > 0 else v_venda
    t = termometro_selection(d, u_row, valor_para_termo, motor)
    return {
        "empreendimento": empreendimento,
        "identificador": identificador,
        "valor_venda_tabela": v_venda,
        "valor_para_termometro": valor_para_termo,
        **t,
    }
