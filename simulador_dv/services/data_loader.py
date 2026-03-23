# -*- coding: utf-8 -*-
"""
Carregamento de dados para a API sem acoplar a `st.session_state`.

Quando o processo Streamlit está ativo, pode reutilizar `st.connection`;
em produção com Uvicorn, usar credenciais em variáveis de ambiente ou
extensão futura com gspread (ver INVENTORY.md).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def load_logins_dataframe() -> pd.DataFrame:
    """
    Tenta obter BD Logins. Em ambiente só Streamlit, usa `st.connection`.
    Caso contrário devolve DataFrame vazio (login API retorna 503 ou use demo).
    """
    try:
        import streamlit as st
        from streamlit_gsheets import GSheetsConnection

        if not hasattr(st, "secrets") or "connections" not in st.secrets:
            return pd.DataFrame()

        conn = st.connection("gsheets", type=GSheetsConnection)
        from simulador_dv.config.constants import ID_GERAL

        df_logins = conn.read(spreadsheet=ID_GERAL, worksheet="BD Logins")
        df_logins.columns = [str(c).strip() for c in df_logins.columns]
        mapa_logins = {
            "Imobiliária/Canal IMOB": "Imobiliaria",
            "Cargo": "Cargo",
            "Nome": "Nome",
            "Email": "Email",
            "Escolha uma senha para o simulador": "Senha",
            "Número de telefone": "Telefone",
        }
        df_logins = df_logins.rename(columns=mapa_logins)
        if "Email" in df_logins.columns:
            df_logins["Email"] = df_logins["Email"].astype(str).str.strip().str.lower()
        if "Senha" in df_logins.columns:
            df_logins["Senha"] = df_logins["Senha"].astype(str).str.strip()
        return df_logins
    except Exception as e:
        logger.debug("load_logins_dataframe: %s", e)
        return pd.DataFrame()
