# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict

from simulador_dv.api.schemas_flow import EstadoSessaoOut


def estado_sessao_out(st: Dict[str, Any]) -> EstadoSessaoOut:
    return EstadoSessaoOut(
        email=st.get("email"),
        passo_simulacao=st.get("passo_simulacao", "input"),
        dados_cliente=st.get("dados_cliente") or {},
        cliente_ativo=bool(st.get("cliente_ativo", False)),
        session_ui=st.get("session_ui") or {},
        unidade_selecionada=st.get("unidade_selecionada"),
        user_name=st.get("user_name"),
        user_phone=st.get("user_phone"),
        user_imobiliaria=st.get("user_imobiliaria"),
        user_cargo=st.get("user_cargo"),
    )
