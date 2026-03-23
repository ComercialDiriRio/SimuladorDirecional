# -*- coding: utf-8 -*-
"""
Gravação em «BD Simulações» (paridade com `aba_simulador_automacao` / summary no Streamlit).
Usa gspread + mesma planilha que `sistema_data.load_sistema_dataframes`.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Tuple

import pandas as pd
import pytz

from simulador_dv.services.sistema_data import (
    _open_spreadsheet_gspread,
    _spreadsheet_id,
    invalidate_sistema_cache,
)

logger = logging.getLogger(__name__)

ABA_DESTINO = "BD Simulações"

# Ordem e nomes alinhados ao cabeçalho da aba «BD Simulações» e ao Streamlit (`nova_linha`).
# Ver também `simulador_dv/docs/PLANILHA_SCHEMA.md`.
COLUNAS_BD_SIMULACOES = [
    "Nome", "CPF", "Data de Nascimento", "Prazo Financiamento",
    "Renda Part. 1", "Renda Part. 4", "Renda Part. 3", "Renda Part. 4.1",
    "Ranking", "Política de Pro Soluto", "Fator Social", "Cotista FGTS",
    "Financiamento Aprovado", "Subsídio Máximo", "Pro Soluto Médio",
    "Capacidade de Entrada", "Poder de Aquisição Médio",
    "Empreendimento Final", "Unidade Final", "Preço Unidade Final",
    "Financiamento Final", "FGTS + Subsídio Final", "Pro Soluto Final",
    "Número de Parcelas do Pro Soluto", "Mensalidade PS",
    "Ato", "Ato 30", "Ato 60", "Ato 90",
    "Renda Part. 2", "Nome do Corretor", "Canal/Imobiliária", "Data/Horário",
    "Sistema de Amortização", "Quantidade Parcelas Financiamento",
    "Quantidade Parcelas Pro Soluto", "Volta ao Caixa",
]


def ensure_bd_simulacoes_header() -> None:
    """Garante que BD Simulações tem o header correto (não 'Coluna 1, 2...')."""
    sh = _open_spreadsheet_gspread()
    if sh is None:
        return
    try:
        ws = sh.worksheet(ABA_DESTINO)
        header_row = ws.row_values(1)
        if not header_row or header_row[0].startswith("Coluna"):
            logger.info("BD Simulações: inicializando header correto (%d colunas)", len(COLUNAS_BD_SIMULACOES))
            ws.clear()
            ws.update(range_name="A1", values=[COLUNAS_BD_SIMULACOES], value_input_option="RAW")
            invalidate_sistema_cache()
        else:
            logger.debug("BD Simulações: header OK (%s...)", header_row[0])
    except Exception as e:
        logger.warning("ensure_bd_simulacoes_header: %s", e)


def build_nova_linha_simulacao(
    d: Dict[str, Any],
    *,
    user_name: str = "",
    user_imobiliaria: str = "",
    volta_caixa: float = 0.0,
) -> Dict[str, Any]:
    """Espelha o dict `nova_linha` em `app.py` (~2128–2147)."""
    rendas_ind = list(d.get("rendas_lista") or [])
    while len(rendas_ind) < 4:
        rendas_ind.append(0.0)
    capacidade_entrada = float(d.get("entrada_total", 0) or 0) + float(d.get("ps_usado", 0) or 0)
    renda = float(d.get("renda", 0) or 0)
    finan_ref = float(d.get("finan_f_ref", 0) or 0)
    sub_ref = float(d.get("sub_f_ref", 0) or 0)
    imovel_valor = float(d.get("imovel_valor", 0) or 0)
    tz = pytz.timezone("America/Sao_Paulo")
    data_hora = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
    return {
        "Nome": d.get("nome"),
        "CPF": d.get("cpf"),
        "Data de Nascimento": str(d.get("data_nascimento")),
        "Prazo Financiamento": d.get("prazo_financiamento"),
        "Renda Part. 1": rendas_ind[0],
        "Renda Part. 4": rendas_ind[3],
        "Renda Part. 3": rendas_ind[2],
        "Renda Part. 4.1": 0.0,
        "Ranking": d.get("ranking"),
        "Política de Pro Soluto": d.get("politica"),
        "Fator Social": "Sim" if d.get("social") else "Não",
        "Cotista FGTS": "Sim" if d.get("cotista") else "Não",
        "Financiamento Aprovado": finan_ref,
        "Subsídio Máximo": sub_ref,
        "Pro Soluto Médio": d.get("ps_usado", 0),
        "Capacidade de Entrada": capacidade_entrada,
        "Poder de Aquisição Médio": (2 * renda) + finan_ref + sub_ref + (imovel_valor * 0.10),
        "Empreendimento Final": d.get("empreendimento_nome"),
        "Unidade Final": d.get("unidade_id"),
        "Preço Unidade Final": imovel_valor,
        "Financiamento Final": d.get("finan_usado", 0),
        "FGTS + Subsídio Final": d.get("fgts_sub_usado", 0),
        "Pro Soluto Final": d.get("ps_usado", 0),
        "Número de Parcelas do Pro Soluto": d.get("ps_parcelas", 0),
        "Mensalidade PS": d.get("ps_mensal", 0),
        "Ato": d.get("ato_final", 0),
        "Ato 30": d.get("ato_30", 0),
        "Ato 60": d.get("ato_60", 0),
        "Ato 90": d.get("ato_90", 0),
        "Renda Part. 2": rendas_ind[1],
        "Nome do Corretor": user_name,
        "Canal/Imobiliária": user_imobiliaria,
        "Data/Horário": data_hora,
        "Sistema de Amortização": d.get("sistema_amortizacao", "SAC"),
        "Quantidade Parcelas Financiamento": d.get("prazo_financiamento", 360),
        "Quantidade Parcelas Pro Soluto": d.get("ps_parcelas", 0),
        "Volta ao Caixa": float(volta_caixa),
    }


def append_linha_bd_simulacoes(nova_linha: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Lê a aba, concatena uma linha e regrava (mesmo padrão do Streamlit).
    """
    sh = _open_spreadsheet_gspread()
    if sh is None:
        return (
            False,
            "Credenciais Google Sheets indisponíveis "
            "(SIMULADOR_GSHEETS_JSON, GOOGLE_APPLICATION_CREDENTIALS ou credentials.json)",
        )

    try:
        ws = sh.worksheet(ABA_DESTINO)
    except Exception as e:
        logger.warning("worksheet %s: %s", ABA_DESTINO, e)
        return False, f"Aba '{ABA_DESTINO}' não encontrada ou sem acesso: {e}"

    try:
        records = ws.get_all_records()
        df_existente = pd.DataFrame(records) if records else pd.DataFrame()
        df_novo = pd.DataFrame([nova_linha])

        if df_existente.empty:
            df_final = df_novo
        else:
            all_cols = list(df_existente.columns)
            for c in df_novo.columns:
                if c not in all_cols:
                    all_cols.append(c)
            df_existente = df_existente.reindex(columns=all_cols)
            df_novo = df_novo.reindex(columns=all_cols)
            df_final = pd.concat([df_existente, df_novo], ignore_index=True)

        # Cabeçalho + linhas (evitar NaN em JSON para Sheets)
        df_final = df_final.where(pd.notnull(df_final), None)
        header = [str(c) for c in df_final.columns.tolist()]
        rows = []
        for _, row in df_final.iterrows():
            rows.append([_cell_for_sheet(v) for v in row.tolist()])
        body = [header] + rows
        ws.clear()
        ws.update(range_name="A1", values=body, value_input_option="USER_ENTERED")
        invalidate_sistema_cache()
        return True, f"Salvo em '{ABA_DESTINO}'"
    except Exception as e:
        logger.exception("append_bd_simulacoes")
        return False, str(e)


def _cell_for_sheet(v: Any) -> Any:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if hasattr(v, "item"):
        try:
            return v.item()
        except Exception:
            pass
    return v


def spreadsheet_id_for_docs() -> str:
    """ID extraído de `ID_GERAL` (para mensagens / links)."""
    return _spreadsheet_id() or ""
