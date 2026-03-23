# -*- coding: utf-8 -*-
"""
Carrega DataFrames do Google Sheets (espelho de `carregar_dados_sistema` em app.py),
sem `st.cache_data`: cache TTL em memória para uso pela API Uvicorn.

Prioridade:
1. Credenciais JSON (GOOGLE_APPLICATION_CREDENTIALS, SIMULADOR_GSHEETS_CREDENTIALS ou credentials.json na raiz).
2. Fallback: tentativa com Streamlit + st.connection (se secrets disponíveis no processo).
"""
from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from simulador_dv.config.constants import ID_GERAL
from simulador_dv.data.politicas_ps import bd_ranking_to_politicas_dataframe
from simulador_dv.data.premissas import DEFAULT_PREMISSAS, premissas_from_dataframe
from simulador_dv.services.format_utils import limpar_area_br, limpar_moeda, limpar_cpf_visual

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
_cache_time: float = 0.0
_cache_payload: Optional[Tuple[Any, ...]] = None

_logins_only_time: float = 0.0
_logins_only_df: Optional[pd.DataFrame] = None


def sistema_cache_ttl_sec() -> float:
    """TTL do cache in-process de `load_sistema_dataframes` / logins-only (env SIMULADOR_SISTEMA_CACHE_TTL_SEC)."""
    try:
        return max(30.0, float(os.environ.get("SIMULADOR_SISTEMA_CACHE_TTL_SEC", "300")))
    except (TypeError, ValueError):
        return 300.0


def normalize_df_logins(df_logins: pd.DataFrame) -> pd.DataFrame:
    """Mesmas colunas que `_load_frames_inner` (BD Logins)."""
    if df_logins is None or df_logins.empty:
        return pd.DataFrame(columns=["Email", "Senha", "Nome", "Cargo", "Imobiliaria", "Telefone"])
    df = df_logins.copy()
    df.columns = [str(c).strip() for c in df.columns]
    mapa_logins = {
        "Imobiliária/Canal IMOB": "Imobiliaria",
        "Cargo": "Cargo",
        "Nome": "Nome",
        "Email": "Email",
        "Escolha uma senha para o simulador": "Senha",
        "Número de telefone": "Telefone",
    }
    df = df.rename(columns=mapa_logins)
    if "Email" in df.columns:
        df["Email"] = df["Email"].astype(str).str.strip().str.lower()
    if "Senha" in df.columns:
        df["Senha"] = df["Senha"].astype(str).str.strip()
    return df


def load_logins_df_only(force_refresh: bool = False) -> pd.DataFrame:
    """
    Lê apenas a aba de logins (1 round-trip Sheets), com cache alinhado ao TTL do sistema.
    Usado no login para não carregar finanças/estoque/políticas/etc.
    """
    global _logins_only_time, _logins_only_df
    now = time.monotonic()
    ttl = sistema_cache_ttl_sec()
    if (
        not force_refresh
        and _logins_only_df is not None
        and not _logins_only_df.empty
        and (now - _logins_only_time) < ttl
    ):
        return _logins_only_df

    ws_name = (os.environ.get("SIMULADOR_LOGINS_WORKSHEET") or "BD Logins").strip() or "BD Logins"
    df_raw = pd.DataFrame()

    sh = _open_spreadsheet_gspread()
    if sh is not None:
        try:
            df_raw = _ws_to_df(sh.worksheet(ws_name))
        except Exception as e:
            logger.debug("load_logins_df_only worksheet %r: %s", ws_name, e)
    else:
        conn = _read_via_streamlit_gsheets()
        if conn is not None:
            try:
                if hasattr(conn, "read"):
                    df_raw = conn.read(spreadsheet=ID_GERAL, worksheet=ws_name)
                else:
                    df_raw = pd.DataFrame()
            except Exception as e:
                logger.debug("load_logins_df_only streamlit %r: %s", ws_name, e)

    if df_raw.empty:
        empty = pd.DataFrame(columns=["Email", "Senha", "Nome", "Cargo", "Imobiliaria", "Telefone"])
        _logins_only_df = empty
        _logins_only_time = now
        return empty

    df = normalize_df_logins(df_raw)
    _logins_only_df = df
    _logins_only_time = now
    logger.info("BD Logins (only): %d linhas", len(df))
    return df


def _spreadsheet_id() -> Optional[str]:
    m = re.search(r"/d/([a-zA-Z0-9-_]+)", ID_GERAL)
    return m.group(1) if m else None


def _credential_path() -> Optional[str]:
    for p in (
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
        os.environ.get("SIMULADOR_GSHEETS_CREDENTIALS"),
        str(ROOT / "credentials.json"),
    ):
        if p and Path(p).is_file():
            return p
    return None


def _ws_to_df(ws) -> pd.DataFrame:
    try:
        from gspread.utils import ValueRenderOption
        records = ws.get_all_records(value_render_option=ValueRenderOption.unformatted)
        return pd.DataFrame(records)
    except Exception as e:
        logger.debug("ws_to_df: %s", e)
        return pd.DataFrame()


def _open_spreadsheet_gspread():
    sid = _spreadsheet_id()
    if not sid:
        return None
    path = _credential_path()
    if not path:
        return None
    try:
        import gspread

        gc = gspread.service_account(filename=path)
        return gc.open_by_key(sid)
    except Exception as e:
        logger.warning("gspread open: %s", e)
        return None


def _read_via_streamlit_gsheets():
    """Reutiliza streamlit_gsheets se `st.secrets` tiver connections."""
    try:
        import streamlit as st
        from streamlit_gsheets import GSheetsConnection

        if not hasattr(st, "secrets") or "connections" not in st.secrets:
            return None
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        logger.debug("streamlit gsheets: %s", e)
        return None


def _load_frames_inner(conn) -> Tuple[pd.DataFrame, ...]:
    """conn: GSheetsConnection-like com .read(spreadsheet=, worksheet=) ou None para gspread path."""

    def limpar_moeda_local(val):
        return limpar_moeda(val)

    # 1. LOGINS
    try:
        if hasattr(conn, "read"):
            df_logins = conn.read(spreadsheet=ID_GERAL, worksheet="BD Logins")
        else:
            df_logins = _ws_to_df(conn.worksheet("BD Logins"))
        df_logins = normalize_df_logins(pd.DataFrame(df_logins))
    except Exception:
        df_logins = pd.DataFrame(columns=["Email", "Senha", "Nome", "Cargo", "Imobiliaria", "Telefone"])

    # 2. BD SIMULAÇÕES (histórico / gravação)
    df_simulacoes = pd.DataFrame()
    try:
        if hasattr(conn, "read"):
            df_simulacoes = conn.read(spreadsheet=ID_GERAL, worksheet="BD Simulações")
        else:
            df_simulacoes = _ws_to_df(conn.worksheet("BD Simulações"))
        df_simulacoes.columns = [str(c).strip() for c in df_simulacoes.columns]
        if "CPF" in df_simulacoes.columns:
            df_simulacoes["CPF"] = df_simulacoes["CPF"].apply(limpar_cpf_visual)
    except Exception:
        df_simulacoes = pd.DataFrame()

    # 2b. BD CLIENTES (lista oficial de clientes)
    df_clientes = pd.DataFrame()
    for ws_cli in ("BD Clientes", "BD Cliente"):
        try:
            if hasattr(conn, "read"):
                df_clientes = conn.read(spreadsheet=ID_GERAL, worksheet=ws_cli)
            else:
                df_clientes = _ws_to_df(conn.worksheet(ws_cli))
            df_clientes.columns = [str(c).strip() for c in df_clientes.columns]
            if "CPF" in df_clientes.columns:
                df_clientes["CPF"] = df_clientes["CPF"].apply(limpar_cpf_visual)
            if not df_clientes.empty:
                break
        except Exception:
            continue

    # 3. POLÍTICAS (BD Ranking tem prioridade se existir)
    df_politicas = pd.DataFrame()
    df_rank_try = pd.DataFrame()
    try:
        if hasattr(conn, "read"):
            df_rank_try = conn.read(spreadsheet=ID_GERAL, worksheet="BD Ranking")
        else:
            df_rank_try = _ws_to_df(conn.worksheet("BD Ranking"))
        df_rank_try.columns = [str(c).strip() for c in df_rank_try.columns]
    except Exception:
        df_rank_try = pd.DataFrame()
    df_from_rank = bd_ranking_to_politicas_dataframe(df_rank_try)
    if not df_from_rank.empty:
        df_politicas = df_from_rank
    else:
        for ws_pol in ("POLITICAS", "BD Politicas", "BD Políticas"):
            try:
                if hasattr(conn, "read"):
                    df_politicas = conn.read(spreadsheet=ID_GERAL, worksheet=ws_pol)
                else:
                    df_politicas = _ws_to_df(conn.worksheet(ws_pol))
                df_politicas.columns = [str(c).strip() for c in df_politicas.columns]
                if not df_politicas.empty:
                    break
            except Exception:
                continue

    # 4. FINAN
    try:
        if hasattr(conn, "read"):
            df_finan = conn.read(spreadsheet=ID_GERAL, worksheet="BD Financiamentos")
        else:
            df_finan = _ws_to_df(conn.worksheet("BD Financiamentos"))
        df_finan.columns = [str(c).strip() for c in df_finan.columns]
        for col in df_finan.columns:
            df_finan[col] = df_finan[col].apply(limpar_moeda_local)
    except Exception:
        df_finan = pd.DataFrame()

    # 5. ESTOQUE (mesma lógica que app.py)
    df_estoque = pd.DataFrame()
    try:
        if hasattr(conn, "read"):
            df_raw = conn.read(spreadsheet=ID_GERAL, worksheet="BD Estoque Filtrada")
        else:
            df_raw = _ws_to_df(conn.worksheet("BD Estoque Filtrada"))
        df_raw.columns = [str(c).strip() for c in df_raw.columns]

        col_valor_venda = "Valor de Venda"
        if "Valor de Venda" not in df_raw.columns:
            if "Valor Comercial Mínimo" in df_raw.columns:
                col_valor_venda = "Valor Comercial Mínimo"

        mapa_estoque = {
            "Nome do Empreendimento": "Empreendimento",
            col_valor_venda: "Valor de Venda",
            "Status da unidade": "Status",
            "Identificador": "Identificador",
            "Bairro": "Bairro",
            "Valor de Avaliação Bancária": "Valor de Avaliação Bancária",
            "PS EmCash": "PS_EmCash",
            "PS Diamante": "PS_Diamante",
            "PS Ouro": "PS_Ouro",
            "PS Prata": "PS_Prata",
            "PS Bronze": "PS_Bronze",
            "PS Aço": "PS_Aco",
            "Previsão de expedição do habite-se": "Data Entrega",
            "Área privativa total": "Area",
            "Tipo Planta/Área": "Tipologia",
            "Endereço": "Endereco",
            "Folga Volta ao Caixa": "Volta_Caixa_Ref",
        }

        mapa_ajustado = {}
        for k, v in mapa_estoque.items():
            if k.strip() in df_raw.columns:
                mapa_ajustado[k.strip()] = v

        df_estoque = df_raw.rename(columns=mapa_ajustado)

        if "Valor de Venda" not in df_estoque.columns:
            df_estoque["Valor de Venda"] = 0.0
        if "Valor de Avaliação Bancária" not in df_estoque.columns:
            df_estoque["Valor de Avaliação Bancária"] = df_estoque["Valor de Venda"]
        if "Status" not in df_estoque.columns:
            df_estoque["Status"] = "Disponível"
        if "Empreendimento" not in df_estoque.columns:
            df_estoque["Empreendimento"] = "N/A"
        if "Data Entrega" not in df_estoque.columns:
            df_estoque["Data Entrega"] = ""
        if "Area" not in df_estoque.columns:
            df_estoque["Area"] = ""
        if "Tipologia" not in df_estoque.columns:
            df_estoque["Tipologia"] = ""
        if "Endereco" not in df_estoque.columns:
            df_estoque["Endereco"] = ""
        if "Volta_Caixa_Ref" not in df_estoque.columns:
            df_estoque["Volta_Caixa_Ref"] = 0.0

        df_estoque["Valor de Venda"] = df_estoque["Valor de Venda"].apply(limpar_moeda_local)
        df_estoque["Valor de Avaliação Bancária"] = df_estoque["Valor de Avaliação Bancária"].apply(limpar_moeda_local)
        df_estoque["Volta_Caixa_Ref"] = df_estoque["Volta_Caixa_Ref"].apply(limpar_moeda_local)

        cols_ps = ["PS_EmCash", "PS_Diamante", "PS_Ouro", "PS_Prata", "PS_Bronze", "PS_Aco"]
        for c in cols_ps:
            if c in df_estoque.columns:
                df_estoque[c] = df_estoque[c].apply(limpar_moeda_local)
            else:
                df_estoque[c] = 0.0

        if "Status" in df_estoque.columns:
            df_estoque["Status"] = df_estoque["Status"].astype(str).str.strip()

        df_estoque = df_estoque[(df_estoque["Valor de Venda"] > 1000)].copy()
        if "Empreendimento" in df_estoque.columns:
            df_estoque = df_estoque[df_estoque["Empreendimento"].notnull()]

        if "Identificador" not in df_estoque.columns:
            df_estoque["Identificador"] = df_estoque.index.astype(str)
        if "Bairro" not in df_estoque.columns:
            df_estoque["Bairro"] = "Rio de Janeiro"

        def extrair_dados_unid(id_unid, tipo):
            try:
                s = str(id_unid)
                p, sx = (s.split("-")[0], s.split("-")[-1]) if "-" in s else (s, s)
                np_val = re.sub(r"\D", "", p)
                ns_val = re.sub(r"\D", "", sx)
                if tipo == "andar":
                    return int(ns_val) // 100 if ns_val else 0
                if tipo == "bloco":
                    return int(np_val) if np_val else 1
                if tipo == "apto":
                    return int(ns_val) if ns_val else 0
            except Exception:
                return 0 if tipo != "bloco" else 1
            return 0

        df_estoque["Andar"] = df_estoque["Identificador"].apply(lambda x: extrair_dados_unid(x, "andar"))
        df_estoque["Bloco_Sort"] = df_estoque["Identificador"].apply(lambda x: extrair_dados_unid(x, "bloco"))
        df_estoque["Apto_Sort"] = df_estoque["Identificador"].apply(lambda x: extrair_dados_unid(x, "apto"))

        if "Empreendimento" in df_estoque.columns:
            df_estoque["Empreendimento"] = df_estoque["Empreendimento"].astype(str).str.strip()
        if "Bairro" in df_estoque.columns:
            df_estoque["Bairro"] = df_estoque["Bairro"].astype(str).str.strip()

        if "Area" in df_estoque.columns:
            df_estoque["Area"] = df_estoque["Area"].apply(limpar_area_br)

        try:
            if hasattr(conn, "read"):
                df_loc = conn.read(spreadsheet=ID_GERAL, worksheet="PROCX Localização - BD Estoque")
            else:
                df_loc = _ws_to_df(conn.worksheet("PROCX Localização - BD Estoque"))
            df_loc.columns = [str(c).strip() for c in df_loc.columns]
            if "Endereço" in df_loc.columns and "Endereco" not in df_loc.columns:
                df_loc = df_loc.rename(columns={"Endereço": "Endereco"})
            if (
                not df_loc.empty
                and "Empreendimento" in df_loc.columns
                and "Empreendimento" in df_estoque.columns
            ):
                loc_small = df_loc.drop_duplicates(subset=["Empreendimento"], keep="first")
                df_estoque = df_estoque.merge(
                    loc_small,
                    on="Empreendimento",
                    how="left",
                    suffixes=("", "_loc"),
                )
                if "Bairro_loc" in df_estoque.columns:
                    b = df_estoque["Bairro"].astype(str).str.strip()
                    mask = (b == "") | (b == "nan") | (b == "Rio de Janeiro")
                    df_estoque.loc[mask, "Bairro"] = df_estoque.loc[mask, "Bairro_loc"].fillna("")
                    df_estoque.drop(columns=["Bairro_loc"], errors="ignore", inplace=True)
                if "Endereco_loc" in df_estoque.columns:
                    if "Endereco" not in df_estoque.columns:
                        df_estoque["Endereco"] = ""
                    e = df_estoque["Endereco"].astype(str).str.strip()
                    em = (e == "") | (e == "nan")
                    df_estoque.loc[em, "Endereco"] = df_estoque.loc[em, "Endereco_loc"].fillna("")
                    df_estoque.drop(columns=["Endereco_loc"], errors="ignore", inplace=True)
                df_estoque.drop(
                    columns=[c for c in df_estoque.columns if c.endswith("_loc")],
                    errors="ignore",
                    inplace=True,
                )
        except Exception:
            pass

    except Exception as e:
        logger.debug("estoque: %s", e)
        df_estoque = pd.DataFrame(
            columns=[
                "Empreendimento",
                "Valor de Venda",
                "Status",
                "Identificador",
                "Bairro",
                "Valor de Avaliação Bancária",
            ]
        )

    premissas_dict: Dict[str, float] = dict(DEFAULT_PREMISSAS)
    for ws_prem in ("BD Premissas", "PREMISSAS"):
        try:
            if hasattr(conn, "read"):
                df_pr = conn.read(spreadsheet=ID_GERAL, worksheet=ws_prem)
            else:
                df_pr = _ws_to_df(conn.worksheet(ws_prem))
            premissas_dict = premissas_from_dataframe(df_pr)
            break
        except Exception:
            continue

    return df_finan, df_estoque, df_politicas, df_logins, df_simulacoes, df_clientes, premissas_dict


def load_sistema_dataframes(force_refresh: bool = False) -> Tuple[
    pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, float]
]:
    """
    Retorna (df_finan, df_estoque, df_politicas, df_logins, df_simulacoes, df_clientes, premissas_dict).
    """
    global _cache_time, _cache_payload, _logins_only_time, _logins_only_df
    now = time.monotonic()
    if not force_refresh and _cache_payload is not None and (now - _cache_time) < sistema_cache_ttl_sec():
        return _cache_payload

    conn = None
    sh = _open_spreadsheet_gspread()
    if sh is not None:
        conn = sh
    else:
        conn = _read_via_streamlit_gsheets()

    if conn is None:
        empty = (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            dict(DEFAULT_PREMISSAS),
        )
        _cache_time = now
        _cache_payload = empty
        _logins_only_df = empty[3]
        _logins_only_time = now
        return empty

    try:
        payload = _load_frames_inner(conn)
    except Exception as e:
        logger.warning("load_sistema_dataframes: %s", e)
        payload = (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            dict(DEFAULT_PREMISSAS),
        )

    _cache_time = now
    _cache_payload = payload
    df_finan, df_estoque, df_politicas, df_logins, df_simulacoes, df_clientes, premissas = payload
    _logins_only_df = df_logins
    _logins_only_time = now
    logger.info(
        "Dados carregados: logins=%d, clientes=%d, simulacoes=%d, estoque=%d, financiamentos=%d, politicas=%d",
        len(df_logins),
        len(df_clientes),
        len(df_simulacoes),
        len(df_estoque),
        len(df_finan),
        len(df_politicas),
    )
    return payload


def invalidate_sistema_cache() -> None:
    """Após gravação na planilha (ex.: BD Simulações), força recarregar na próxima leitura."""
    global _cache_time, _cache_payload, _logins_only_time, _logins_only_df
    _cache_time = 0.0
    _cache_payload = None
    _logins_only_time = 0.0
    _logins_only_df = None
    try:
        from simulador_dv.api.data_context import clear_simulador_context_cache

        clear_simulador_context_cache()
    except Exception:
        pass
