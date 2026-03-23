# -*- coding: utf-8 -*-
"""HTML do passo `summary` (paridade com `app.py` ~L2081–L2109)."""
from __future__ import annotations

from typing import Any, Dict, List

from simulador_dv.config.constants import COR_VERMELHO
from simulador_dv.services.format_utils import fmt_br


def build_resumo_html_secoes(dados: Dict[str, Any]) -> List[Dict[str, str]]:
    """Devolve lista de secções com título e HTML para injetar no front."""
    d = dados or {}
    secoes: List[Dict[str, str]] = []

    secoes.append(
        {
            "id": "imovel",
            "titulo": "DADOS DO IMÓVEL",
            "html": f"""
<div class="summary-body">
<b>Empreendimento:</b> {d.get('empreendimento_nome') or '—'}<br>
<b>Unidade:</b> {d.get('unidade_id') or '—'}<br>
<b>Valor Comercial (Venda):</b> <span style="color: {COR_VERMELHO}; font-weight: 800;">R$ {fmt_br(d.get('imovel_valor', 0))}</span><br>
<b>Avaliação Bancária:</b> R$ {fmt_br(d.get('imovel_avaliacao', 0))}
</div>""".strip(),
        }
    )

    detalhes_parts = []
    if d.get("unid_entrega"):
        detalhes_parts.append(f"<b>Previsão de Entrega:</b> {d.get('unid_entrega')}<br>")
    if d.get("unid_area"):
        detalhes_parts.append(f"<b>Área Privativa Total:</b> {d.get('unid_area')} m²<br>")
    if d.get("unid_tipo"):
        detalhes_parts.append(f"<b>Tipo Planta/Área:</b> {d.get('unid_tipo')}<br>")
    if d.get("unid_endereco") and d.get("unid_bairro"):
        detalhes_parts.append(f"<b>Localização:</b> {d.get('unid_endereco')} - {d.get('unid_bairro')}")
    if detalhes_parts:
        secoes.append(
            {
                "id": "detalhes_unidade",
                "titulo": "DETALHES DA UNIDADE",
                "html": f'<div class="summary-body">{"".join(detalhes_parts)}</div>',
            }
        )

    prazo_txt = d.get("prazo_financiamento", 360)
    parcela_texto = (
        f"Parcela Estimada ({d.get('sistema_amortizacao', 'SAC')} - {prazo_txt}x): "
        f"R$ {fmt_br(d.get('parcela_financiamento', 0))}"
    )
    secoes.append(
        {
            "id": "financiamento",
            "titulo": "PLANO DE FINANCIAMENTO",
            "html": f"""<div class="summary-body"><b>Financiamento Bancário:</b> R$ {fmt_br(d.get('finan_usado', 0))}<br><b>{parcela_texto}</b><br><b>FGTS + Subsídio:</b> R$ {fmt_br(d.get('fgts_sub_usado', 0))}<br><b>Pro Soluto Total:</b> R$ {fmt_br(d.get('ps_usado', 0))} ({d.get('ps_parcelas')}x de R$ {fmt_br(d.get('ps_mensal', 0))})</div>""",
        }
    )

    secoes.append(
        {
            "id": "entrada",
            "titulo": "FLUXO DE ENTRADA (ATO)",
            "html": f"""<div class="summary-body"><b>Total de Entrada:</b> R$ {fmt_br(d.get('entrada_total', 0))}<br><hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 10px 0;"><b>Ato:</b> R$ {fmt_br(d.get('ato_final', 0))}<br><b>Ato 30 Dias:</b> R$ {fmt_br(d.get('ato_30', 0))}<br><b>Ato 60 Dias:</b> R$ {fmt_br(d.get('ato_60', 0))}<br><b>Ato 90 Dias:</b> R$ {fmt_br(d.get('ato_90', 0))}</div>""",
        }
    )

    return secoes


def titulo_resumo_cliente(dados: Dict[str, Any]) -> str:
    return f"Resumo da Simulação - {dados.get('nome', 'Cliente') or 'Cliente'}"
