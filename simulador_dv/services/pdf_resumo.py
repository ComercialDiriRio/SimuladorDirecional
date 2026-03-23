# -*- coding: utf-8 -*-
"""Geração de PDF de resumo (extraído de app.py)."""
from __future__ import annotations

import logging
import os
from datetime import date
from typing import Any, Dict, Optional

from simulador_dv.services.format_utils import fmt_br

logger = logging.getLogger(__name__)

try:
    from fpdf import FPDF

    PDF_ENABLED = True
    logger.info("fpdf2 carregado com sucesso (PDF_ENABLED=True, versão=%s)", getattr(FPDF, '__module__', 'fpdf'))
except ImportError as _imp_err:
    PDF_ENABLED = False
    FPDF = None  # type: ignore
    logger.warning("fpdf2 não disponível — geração de PDF desativada: %s", _imp_err)
except Exception as _exc:
    PDF_ENABLED = False
    FPDF = None  # type: ignore
    logger.exception("Erro inesperado ao importar fpdf2: %s", _exc)


def gerar_resumo_pdf(d: Dict[str, Any]) -> Optional[bytes]:
    if not PDF_ENABLED or FPDF is None:
        logger.warning("gerar_resumo_pdf: PDF_ENABLED=%s, FPDF=%s", PDF_ENABLED, FPDF)
        return None

    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_margins(12, 12, 12)
        pdf.set_auto_page_break(auto=True, margin=12)
        largura_util = pdf.w - pdf.l_margin - pdf.r_margin

        AZUL = (0, 44, 93)
        VERMELHO = (227, 6, 19)
        BRANCO = (255, 255, 255)
        FUNDO_SECAO = (248, 250, 252)

        pdf.set_fill_color(*AZUL)
        pdf.rect(0, 0, pdf.w, 3, "F")

        if os.path.exists("favicon.png"):
            try:
                pdf.image("favicon.png", pdf.l_margin, 8, 10)
            except Exception:
                pass

        pdf.ln(8)
        pdf.set_text_color(*AZUL)
        pdf.set_font("Helvetica", "B", 20)
        pdf.cell(0, 10, "RELATÓRIO DE VIABILIDADE", ln=True, align="C")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, "SIMULADOR IMOBILIARIO DV - DOCUMENTO EXECUTIVO", ln=True, align="C")
        pdf.ln(6)

        y = pdf.get_y()
        pdf.set_fill_color(*FUNDO_SECAO)
        pdf.rect(pdf.l_margin, y, largura_util, 16, "F")
        pdf.set_xy(pdf.l_margin + 4, y + 4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 5, f"CLIENTE: {d.get('nome', 'Não informado').upper()}", ln=True)
        pdf.set_x(pdf.l_margin + 4)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 5, f"Renda Familiar: R$ {fmt_br(d.get('renda', 0))}", ln=True)
        pdf.ln(6)

        def secao(titulo: str) -> None:
            pdf.set_fill_color(*AZUL)
            pdf.set_text_color(*BRANCO)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(largura_util, 7, f"  {titulo}", ln=True, fill=True)
            pdf.ln(2)

        def linha(label: str, valor: str, destaque: bool = False) -> None:
            pdf.set_text_color(*AZUL)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(largura_util * 0.6, 6, label)
            if destaque:
                pdf.set_text_color(*VERMELHO)
                pdf.set_font("Helvetica", "B", 10)
            else:
                pdf.set_font("Helvetica", "B", 10)
            pdf.cell(largura_util * 0.4, 6, valor, ln=True, align="R")
            pdf.set_draw_color(235, 238, 242)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + largura_util, pdf.get_y())

        secao("DADOS DO IMÓVEL")
        linha("Empreendimento", str(d.get("empreendimento_nome")))
        linha("Unidade Selecionada", str(d.get("unidade_id")))
        v_comercial = d.get("imovel_valor", 0)
        v_avaliacao = d.get("imovel_avaliacao", 0)
        linha("Valor de Tabela/Avaliação", f"R$ {fmt_br(v_avaliacao)}", True)
        if d.get("unid_entrega"):
            linha("Previsão de Entrega", str(d.get("unid_entrega")))
        if d.get("unid_area"):
            linha("Área Privativa", f"{d.get('unid_area')} m²")
        if d.get("unid_tipo"):
            linha("Tipologia", str(d.get("unid_tipo")))
        if d.get("unid_endereco") and d.get("unid_bairro"):
            linha("Endereço", f"{d.get('unid_endereco')} - {d.get('unid_bairro')}")
        pdf.ln(4)

        secao("CONDIÇÃO COMERCIAL")
        desconto = max(0, float(v_avaliacao or 0) - float(v_comercial or 0))
        linha("Desconto/Condição Especial", f"R$ {fmt_br(desconto)}")
        linha("Valor Final de Venda", f"R$ {fmt_br(v_comercial)}", True)
        pdf.ln(4)

        secao("ENGENHARIA FINANCEIRA")
        linha("Financiamento Bancário Estimado", f"R$ {fmt_br(d.get('finan_usado', 0))}")
        prazo = d.get("prazo_financiamento", 360)
        linha("Sistema de Amortização", f"{d.get('sistema_amortizacao', 'SAC')} - {prazo}x")
        linha("Parcela Estimada do Financiamento", f"R$ {fmt_br(d.get('parcela_financiamento', 0))}")
        linha("Subsídio + FGTS Utilizado", f"R$ {fmt_br(d.get('fgts_sub_usado', 0))}")
        linha("Pro Soluto Direcional", f"R$ {fmt_br(d.get('ps_usado', 0))}")
        linha("Mensalidade do Pro Soluto", f"{d.get('ps_parcelas')}x de R$ {fmt_br(d.get('ps_mensal', 0))}")
        pdf.ln(4)

        secao("FLUXO DE ENTRADA (ATO)")
        linha("Valor Total de Entrada", f"R$ {fmt_br(d.get('entrada_total', 0))}", True)
        linha("Ato (Imediato)", f"R$ {fmt_br(d.get('ato_final', 0))}")
        linha("Ato 30 Dias", f"R$ {fmt_br(d.get('ato_30', 0))}")
        linha("Ato 60 Dias", f"R$ {fmt_br(d.get('ato_60', 0))}")
        linha("Ato 90 Dias", f"R$ {fmt_br(d.get('ato_90', 0))}")
        pdf.ln(4)

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*AZUL)
        pdf.cell(0, 5, "CONSULTOR RESPONSÁVEL", ln=True, align="L")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, f"{d.get('corretor_nome', 'Não informado').upper()}", ln=True)
        pdf.cell(0, 5, f"Contato: {d.get('corretor_telefone', '')} | E-mail: {d.get('corretor_email', '')}", ln=True)
        pdf.ln(4)

        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(
            0,
            4,
            f"Simulação realizada em {d.get('data_simulacao', date.today().strftime('%d/%m/%Y'))}. "
            "Sujeito a análise de crédito e alteração de tabela sem aviso prévio.",
            ln=True,
            align="C",
        )
        pdf.cell(0, 4, "Direcional Engenharia - Rio de Janeiro", ln=True, align="C")

        out = pdf.output()
        return bytes(out)
    except Exception:
        logger.exception("gerar_resumo_pdf: falha na geração")
        return None
