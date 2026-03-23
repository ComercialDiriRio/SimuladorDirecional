# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Annotated, Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Response

from simulador_dv.api.deps import require_session_state
from simulador_dv.api.schemas_flow import EmailRequest, PdfRequest, ResumoOut, SalvarSimulacaoOut
from simulador_dv.api.session_store import update_session
from simulador_dv.services.email_smtp import enviar_email_smtp
from simulador_dv.services.pdf_resumo import gerar_resumo_pdf
from simulador_dv.services.resumo_html import build_resumo_html_secoes, titulo_resumo_cliente
from simulador_dv.services.simulacao_sheets import append_linha_bd_simulacoes, build_nova_linha_simulacao

router = APIRouter(tags=["resumo"])


@router.get("/resumo", response_model=ResumoOut)
def get_resumo(st: Annotated[dict, Depends(require_session_state)]) -> ResumoOut:
    return ResumoOut(
        dados_cliente=st.get("dados_cliente") or {},
        unidade_selecionada=st.get("unidade_selecionada"),
        passo_simulacao=st.get("passo_simulacao", "input"),
    )


@router.get("/resumo/blocos-html")
def get_resumo_blocos_html(st: Annotated[dict, Depends(require_session_state)]) -> Dict[str, Any]:
    """Secções HTML equivalentes ao passo `summary` no Streamlit."""
    dados = st.get("dados_cliente") or {}
    return {
        "titulo": titulo_resumo_cliente(dados),
        "secoes": build_resumo_html_secoes(dados),
    }


@router.post("/pdf")
def post_pdf(
    st: Annotated[dict, Depends(require_session_state)],
    body: Optional[PdfRequest] = Body(default=None),
) -> Response:
    dados = dict(st.get("dados_cliente") or {})
    dados.setdefault("corretor_nome", st.get("user_name") or "")
    dados.setdefault("corretor_email", st.get("email") or "")
    dados.setdefault("corretor_telefone", st.get("user_phone") or "")
    if body and body.dados:
        dados.update(body.dados)
    pdf_bytes = gerar_resumo_pdf(dados)
    if not pdf_bytes:
        raise HTTPException(status_code=503, detail="PDF indisponível (fpdf ou dados)")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="resumo_simulacao.pdf"'},
    )


@router.post("/email")
def post_email(
    st: Annotated[dict, Depends(require_session_state)],
    body: EmailRequest,
) -> Dict[str, Any]:
    dados = dict(st.get("dados_cliente") or {})
    dados.setdefault("corretor_nome", st.get("user_name") or "")
    dados.setdefault("corretor_email", st.get("email") or "")
    dados.setdefault("corretor_telefone", st.get("user_phone") or "")
    if body.dados:
        dados.update(body.dados)
    pdf_bytes = gerar_resumo_pdf(dados)
    ok, msg = enviar_email_smtp(
        body.destinatario,
        body.nome_cliente,
        pdf_bytes,
        dados,
        tipo=body.tipo,
    )
    if not ok:
        raise HTTPException(status_code=503, detail=msg)
    return {"ok": True, "message": msg}


@router.post("/salvar-simulacao", response_model=SalvarSimulacaoOut)
def post_salvar_simulacao(
    st: Annotated[dict, Depends(require_session_state)],
) -> SalvarSimulacaoOut:
    """
    Grava linha em «BD Simulações» (paridade com botão CONCLUIR E SALVAR SIMULAÇÃO no Streamlit).
    Em sucesso, reinicia `dados_cliente` e passo para `input`, como no `st.rerun` do app.
    """
    sid = st["_session_id"]
    dados = dict(st.get("dados_cliente") or {})
    sui = st.get("session_ui") or {}
    vc = float(sui.get("volta_caixa_key") or dados.get("volta_caixa_input") or 0)
    nova = build_nova_linha_simulacao(
        dados,
        user_name=str(st.get("user_name") or ""),
        user_imobiliaria=str(st.get("user_imobiliaria") or ""),
        volta_caixa=vc,
    )
    ok, msg = append_linha_bd_simulacoes(nova)
    if not ok:
        raise HTTPException(status_code=503, detail=msg)
    updated = update_session(
        sid,
        {
            "dados_cliente": {},
            "passo_simulacao": "input",
            "cliente_ativo": False,
            "unidade_selecionada": None,
        },
    )
    assert updated is not None
    return SalvarSimulacaoOut(ok=True, message=msg, reset_sessao=True)
