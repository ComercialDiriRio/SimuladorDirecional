# -*- coding: utf-8 -*-
"""Recomendações IDEAL / SEGURO / FACILITADO (espelho da etapa `guide` em app.py)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd


def _row_to_dict(row: pd.Series) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in row.items():
        try:
            if pd.isna(v):
                out[str(k)] = None
            elif hasattr(v, "item"):
                out[str(k)] = v.item()
            else:
                out[str(k)] = v
        except Exception:
            out[str(k)] = str(v)
    return out


def aplicar_viabilidade(df_estoque: pd.DataFrame, d: Dict[str, Any]) -> pd.DataFrame:
    if df_estoque.empty:
        return df_estoque

    def calcular_viabilidade_unidade(row):
        v_venda = row.get("Valor de Venda", 0)
        v_aval = row.get("Valor de Avaliação Bancária", 0)
        try:
            v_venda = float(v_venda)
        except Exception:
            v_venda = 0.0
        try:
            v_aval = float(v_aval)
        except Exception:
            v_aval = v_venda
        fin = float(d.get("finan_usado", 0) or 0)
        sub = float(d.get("fgts_sub_usado", 0) or 0)
        pol = d.get("politica", "Direcional")
        rank = d.get("ranking", "DIAMANTE")
        ps_max_val = 0.0
        if pol == "Emcash":
            ps_max_val = float(row.get("PS_EmCash", 0.0) or 0)
        else:
            col_rank = f"PS_{rank.title()}" if rank else "PS_Diamante"
            if rank == "AÇO":
                col_rank = "PS_Aco"
            ps_max_val = float(row.get(col_rank, 0.0) or 0)
        capacity = ps_max_val + fin + sub + (2 * float(d.get("renda", 0) or 0))
        cobertura = (capacity / v_venda) * 100 if v_venda > 0 else 0
        is_viavel = capacity >= v_venda
        return pd.Series([capacity, cobertura, is_viavel, fin, sub])

    df = df_estoque.copy()
    df[["Poder_Compra", "Cobertura", "Viavel", "Finan_Unid", "Sub_Unid"]] = df.apply(
        calcular_viabilidade_unidade, axis=1
    )
    return df


def build_guide_payload(
    df_estoque: pd.DataFrame,
    dados_cliente: Dict[str, Any],
    empreendimento_filtro: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retorna empreendimentos viáveis (contagem), grupos IDEAL/SEGURO/FACILITADO e linhas serializáveis.
    """
    df_disp_total = aplicar_viabilidade(df_estoque, dados_cliente)
    if df_disp_total.empty:
        return {
            "empreendimentos_viaveis": [],
            "ideal": [],
            "seguro": [],
            "facilitado": [],
            "mensagem": "Sem estoque disponível.",
        }

    df_viaveis = df_disp_total[df_disp_total["Viavel"]].copy()

    emp_counts: Dict[str, int] = {}
    if not df_viaveis.empty:
        emp_counts = df_viaveis.groupby("Empreendimento").size().to_dict()

    empreendimentos_viaveis = [{"empreendimento": k, "unidades_viaveis": int(v)} for k, v in emp_counts.items()]

    df_pool = df_disp_total
    if empreendimento_filtro and empreendimento_filtro not in ("", "Todos"):
        df_pool = df_disp_total[df_disp_total["Empreendimento"] == empreendimento_filtro]

    if df_pool.empty:
        return {
            "empreendimentos_viaveis": empreendimentos_viaveis,
            "ideal": [],
            "seguro": [],
            "facilitado": [],
            "mensagem": "Nenhuma unidade no filtro.",
        }

    pool_viavel = df_pool[df_pool["Viavel"]]
    cand_facil = pd.DataFrame()
    cand_ideal = pd.DataFrame()
    cand_seguro = pd.DataFrame()

    if not pool_viavel.empty:
        poder = pool_viavel["Poder_Compra"].max()

        def _closest_below(df_v: pd.DataFrame, threshold: float) -> pd.DataFrame:
            below = df_v[df_v["Valor de Venda"] <= threshold]
            if below.empty:
                return pd.DataFrame()
            max_val = below["Valor de Venda"].max()
            return below[below["Valor de Venda"] == max_val]

        cand_ideal = _closest_below(pool_viavel, poder)
        cand_seguro = _closest_below(pool_viavel, 0.9 * poder)
        cand_facil = _closest_below(pool_viavel, 0.75 * poder)
    else:
        fallback_pool = df_pool.sort_values("Valor de Venda", ascending=True)
        if not fallback_pool.empty:
            min_p = fallback_pool["Valor de Venda"].min()
            cand_facil = fallback_pool[fallback_pool["Valor de Venda"] == min_p].head(5)
            max_p = fallback_pool["Valor de Venda"].max()
            cand_ideal = fallback_pool[fallback_pool["Valor de Venda"] == max_p].head(5)
            cand_seguro = fallback_pool.iloc[[len(fallback_pool) // 2]]

    def cards_from_df(label: str, df_g: pd.DataFrame) -> List[Dict[str, Any]]:
        if df_g is None or df_g.empty:
            return []
        df_u = df_g.drop_duplicates(subset=["Identificador"])
        out: List[Dict[str, Any]] = []
        for _, row in df_u.head(6).iterrows():
            out.append({"perfil": label, "row": _row_to_dict(row)})
        return out

    ideal = cards_from_df("IDEAL", cand_ideal)
    seguro = cards_from_df("SEGURO", cand_seguro)
    facilitado = cards_from_df("FACILITADO", cand_facil)

    return {
        "empreendimentos_viaveis": empreendimentos_viaveis,
        "ideal": ideal,
        "seguro": seguro,
        "facilitado": facilitado,
        "mensagem": "",
    }
