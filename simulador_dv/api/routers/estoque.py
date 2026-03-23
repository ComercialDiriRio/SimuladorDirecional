# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from simulador_dv.api.deps import require_session_state
from simulador_dv.api.schemas_flow import UnidadeSelecionarIn
from simulador_dv.api.session_store import update_session
from simulador_dv.services.format_utils import fmt_br
from simulador_dv.services.recomendacoes_guide import aplicar_viabilidade
from simulador_dv.services.sistema_data import load_sistema_dataframes

router = APIRouter(prefix="/estoque", tags=["estoque"])


@router.get("/filtros-meta")
def get_filtros_meta(
    st: Annotated[dict, Depends(require_session_state)],
) -> Dict[str, Any]:
    """Uma leitura de estoque: listas para selects do separador Estoque (evita GET duplicado no guia)."""
    _ = st["_session_id"]
    _, df_estoque, _, _, _, _, _ = load_sistema_dataframes()
    if df_estoque.empty or "Empreendimento" not in df_estoque.columns:
        return {"empreendimentos": [], "bairros": []}
    emps = sorted({str(x).strip() for x in df_estoque["Empreendimento"].dropna().unique()})
    bairros: List[str] = []
    if "Bairro" in df_estoque.columns:
        bairros = sorted({str(x).strip() for x in df_estoque["Bairro"].dropna().unique() if str(x).strip()})
    return {"empreendimentos": emps, "bairros": bairros}


@router.get("/empreendimentos")
def get_empreendimentos(
    st: Annotated[dict, Depends(require_session_state)],
) -> Dict[str, Any]:
    _ = st["_session_id"]
    _, df_estoque, _, _, _, _, _ = load_sistema_dataframes()
    if df_estoque.empty or "Empreendimento" not in df_estoque.columns:
        return {"empreendimentos": []}
    emps = sorted({str(x).strip() for x in df_estoque["Empreendimento"].dropna().unique()})
    return {"empreendimentos": emps}


@router.get("/unidades")
def get_unidades_por_empreendimento(
    st: Annotated[dict, Depends(require_session_state)],
    empreendimento: str = Query(..., description="Nome exato do empreendimento"),
) -> Dict[str, Any]:
    _ = st["_session_id"]
    _, df_estoque, _, _, _, _, _ = load_sistema_dataframes()
    df = df_estoque[df_estoque["Empreendimento"].astype(str).str.strip() == empreendimento.strip()].copy()
    if df.empty:
        return {"unidades": [], "total": 0}
    for c in ["Bloco_Sort", "Andar", "Apto_Sort"]:
        if c not in df.columns:
            df[c] = 0
    df = df.sort_values(["Bloco_Sort", "Andar", "Apto_Sort"])
    out = []
    for _, r in df.iterrows():
        uid = str(r.get("Identificador", ""))
        v_aval = r.get("Valor de Avaliação Bancária", 0)
        v_venda = r.get("Valor de Venda", 0)
        out.append(
            {
                "identificador": uid,
                "label": f"{uid} | Aval: R$ {fmt_br(v_aval)} | Venda: R$ {fmt_br(v_venda)}",
                "valor_avaliacao": float(v_aval or 0),
                "valor_venda": float(v_venda or 0),
                "row": _df_to_records(pd.DataFrame([r]))[0],
            }
        )
    return {"unidades": out, "total": len(out)}


def _df_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df.empty:
        return []
    # serializar tipos numpy
    return df.astype(object).where(pd.notnull(df), None).to_dict(orient="records")


@router.get("")
def get_estoque(
    st: Annotated[dict, Depends(require_session_state)],
    bairro: Optional[str] = Query(None, description="Vírgula: Bairro1,Bairro2"),
    empreendimento: Optional[str] = Query(None, description="Vírgula"),
    cobertura_min_pct: float = Query(0.0),
    ordem: str = Query("menor_preco"),
    preco_max: Optional[float] = Query(None),
) -> Dict[str, Any]:
    _ = st["_session_id"]
    dados = st.get("dados_cliente") or {}
    _, df_estoque, _, _, _, _, _ = load_sistema_dataframes()
    df_disp = aplicar_viabilidade(df_estoque, dados)
    if df_disp.empty:
        return {"itens": [], "total": 0}

    df_tab = df_disp.copy()
    if bairro:
        bs = [x.strip() for x in bairro.split(",") if x.strip()]
        if bs:
            df_tab = df_tab[df_tab["Bairro"].isin(bs)]
    if empreendimento:
        es = [x.strip() for x in empreendimento.split(",") if x.strip()]
        if es:
            df_tab = df_tab[df_tab["Empreendimento"].isin(es)]
    df_tab = df_tab[df_tab["Cobertura"] >= cobertura_min_pct]
    if preco_max is not None:
        df_tab = df_tab[df_tab["Valor de Venda"] <= preco_max]

    asc = ordem == "menor_preco"
    df_tab = df_tab.sort_values("Valor de Venda", ascending=asc)

    cols = [
        "Identificador",
        "Bairro",
        "Empreendimento",
        "Valor de Avaliação Bancária",
        "Valor de Venda",
        "Poder_Compra",
        "Cobertura",
    ]
    for c in cols:
        if c not in df_tab.columns:
            df_tab[c] = None
    df_tab = df_tab[cols]
    recs = _df_to_records(df_tab)
    return {"itens": recs, "total": len(recs)}


@router.post("/selecionar")
def post_selecionar(
    body: UnidadeSelecionarIn,
    st: Annotated[dict, Depends(require_session_state)],
) -> Dict[str, Any]:
    sid = st["_session_id"]
    dados = st.get("dados_cliente") or {}
    _, df_estoque, _, _, _, _, _ = load_sistema_dataframes()
    df_disp = aplicar_viabilidade(df_estoque, dados)
    row = df_disp[df_disp["Identificador"].astype(str) == str(body.identificador)]
    if row.empty:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")
    r = row.iloc[0]
    unidade = {
        "identificador": str(r.get("Identificador", "")),
        "empreendimento": str(r.get("Empreendimento", "")),
        "valor_venda": float(r.get("Valor de Venda", 0) or 0),
        "valor_avaliacao": float(r.get("Valor de Avaliação Bancária", 0) or 0),
        "bairro": str(r.get("Bairro", "")),
    }
    # espelha chaves usadas no PDF / resumo
    patch_dc = {
        "empreendimento_nome": unidade["empreendimento"],
        "unidade_id": unidade["identificador"],
        "imovel_valor": unidade["valor_venda"],
        "imovel_avaliacao": unidade["valor_avaliacao"],
        "unid_bairro": unidade["bairro"],
    }
    if "Area" in r.index:
        patch_dc["unid_area"] = str(r.get("Area", ""))
    if "Tipologia" in r.index:
        patch_dc["unid_tipo"] = str(r.get("Tipologia", ""))
    if "Endereco" in r.index:
        patch_dc["unid_endereco"] = str(r.get("Endereco", ""))
    if "Data Entrega" in r.index:
        patch_dc["unid_entrega"] = str(r.get("Data Entrega", ""))

    update_session(sid, {"dados_cliente": patch_dc, "unidade_selecionada": unidade})
    return {"ok": True, "unidade": unidade}
