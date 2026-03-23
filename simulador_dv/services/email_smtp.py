# -*- coding: utf-8 -*-
"""Envio de e-mail com anexo PDF (extraído de app.py; sem st.secrets)."""
from __future__ import annotations

import os
import re
import smtplib
import urllib.parse
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional, Tuple

from simulador_dv.services.format_utils import fmt_br
from simulador_dv.services.secrets_loader import load_secrets_toml


def _email_config() -> Optional[Dict[str, Any]]:
    """
    SMTP por variáveis de ambiente (Vercel / CI). Ordem:
    1) SIMULADOR_SMTP_* (preferido)
    2) SMTP_* / EMAIL_SMTP_* (aliases curtos)
    3) .streamlit/secrets.toml secção [email]
    """
    server = (
        (os.environ.get("SIMULADOR_SMTP_SERVER") or "").strip()
        or (os.environ.get("SMTP_SERVER") or "").strip()
        or (os.environ.get("EMAIL_SMTP_SERVER") or "").strip()
    )
    if server:
        try:
            port = int(
                os.environ.get("SIMULADOR_SMTP_PORT")
                or os.environ.get("SMTP_PORT")
                or os.environ.get("EMAIL_SMTP_PORT")
                or "587"
            )
        except ValueError:
            port = 587
        user = (
            (os.environ.get("SIMULADOR_SMTP_USER") or "").strip()
            or (os.environ.get("SMTP_USER") or "").strip()
            or (os.environ.get("EMAIL_SMTP_USER") or "").strip()
        )
        password = (
            (os.environ.get("SIMULADOR_SMTP_PASSWORD") or "")
            or (os.environ.get("SMTP_PASSWORD") or "")
            or (os.environ.get("EMAIL_SMTP_PASSWORD") or "")
        ).strip().replace(" ", "")
        return {
            "smtp_server": server,
            "smtp_port": port,
            "sender_email": user,
            "sender_password": password,
        }
    secrets = load_secrets_toml()
    em = secrets.get("email")
    if isinstance(em, dict) and em.get("smtp_server"):
        return {
            "smtp_server": str(em["smtp_server"]).strip(),
            "smtp_port": int(em.get("smtp_port", 587)),
            "sender_email": str(em.get("sender_email", "")).strip(),
            "sender_password": str(em.get("sender_password", "")).strip().replace(" ", ""),
        }
    return None


def enviar_email_smtp(
    destinatario: str,
    nome_cliente: str,
    pdf_bytes: Optional[bytes],
    dados_cliente: Dict[str, Any],
    tipo: str = "cliente",
) -> Tuple[bool, str]:
    cfg = _email_config()
    if not cfg:
        return (
            False,
            "Configurações de e-mail não encontradas "
            "(SIMULADOR_SMTP_* / SMTP_* / secrets.toml [email]).",
        )

    try:
        smtp_server = cfg["smtp_server"]
        smtp_port = int(cfg["smtp_port"])
        sender_email = cfg["sender_email"]
        sender_password = cfg["sender_password"]
    except Exception as e:
        return False, f"Erro config: {e}"

    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = destinatario

    emp = dados_cliente.get("empreendimento_nome", "Seu Imóvel")
    unid = dados_cliente.get("unidade_id", "")
    val_venda = fmt_br(dados_cliente.get("imovel_valor", 0))
    val_aval = fmt_br(dados_cliente.get("imovel_avaliacao", 0))
    entrada = fmt_br(dados_cliente.get("entrada_total", 0))
    finan = fmt_br(dados_cliente.get("finan_usado", 0))
    ps = fmt_br(dados_cliente.get("ps_mensal", 0))
    renda_cli = fmt_br(dados_cliente.get("renda", 0))
    a0 = fmt_br(dados_cliente.get("ato_final", 0))
    a30 = fmt_br(dados_cliente.get("ato_30", 0))
    a60 = fmt_br(dados_cliente.get("ato_60", 0))
    a90 = fmt_br(dados_cliente.get("ato_90", 0))
    corretor_nome = dados_cliente.get("corretor_nome", "Direcional")
    corretor_tel = dados_cliente.get("corretor_telefone", "")
    corretor_email = dados_cliente.get("corretor_email", "")

    corretor_tel_clean = re.sub(r"\D", "", corretor_tel)
    if not corretor_tel_clean.startswith("55"):
        corretor_tel_clean = "55" + corretor_tel_clean

    wa_msg = (
        f"Olá {corretor_nome}, sou {nome_cliente}. Realizei uma simulação para o {emp} "
        f"(Unidade {unid}) e gostaria de saber mais detalhes."
    )
    wa_link = f"https://wa.me/{corretor_tel_clean}?text={urllib.parse.quote(wa_msg)}"
    URL_LOGO_BRANCA = "https://drive.google.com/uc?export=view&id=1m0iX6FCikIBIx4gtSX3Y_YMYxxND2wAh"

    if tipo == "cliente":
        msg["Subject"] = f"Seu sonho está próximo! Simulação - {emp}"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        </head>
        <body style="font-family: 'Helvetica', Arial, sans-serif; color: #333; background-color: #f9f9f9; margin: 0; padding: 20px;">
            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                <tr>
                    <td align="center">
                        <table width="600" border="0" cellspacing="0" cellpadding="0" style="background-color: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                            <tr>
                                <td align="center" style="background-color: #002c5d; padding: 30px; border-bottom: 4px solid #e30613;">
                                    <img src="{URL_LOGO_BRANCA}" width="150" style="display: block;">
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 40px;">
                                    <h2 style="color: #002c5d; margin: 0 0 20px 0; font-weight: 300; text-align: center;">Olá, {nome_cliente}!</h2>
                                    <p style="font-size: 16px; line-height: 1.6; text-align: center; color: #555;">
                                        Foi ótimo apresentar as oportunidades da Direcional para você. O imóvel <strong>{emp}</strong> é incrível e desenhamos uma condição especial para o seu perfil.
                                    </p>
                                    <table width="100%" border="0" cellspacing="0" cellpadding="20" style="background-color: #f0f4f8; border-left: 5px solid #e30613; margin: 30px 0; border-radius: 4px;">
                                        <tr>
                                            <td>
                                                <p style="margin: 0; font-weight: bold; color: #002c5d; font-size: 18px;">{emp}</p>
                                                <p style="margin: 5px 0 0 0; color: #777;">Unidade: {unid}</p>
                                                <p style="margin: 15px 0 0 0; font-size: 24px; font-weight: bold; color: #e30613;">Valor Promocional: R$ {val_venda}</p>
                                            </td>
                                        </tr>
                                    </table>
                                    <div style="text-align: center; margin: 35px 0;">
                                        <a href="{wa_link}" style="background-color: #25D366; color: #ffffff; padding: 15px 30px; text-decoration: none; font-weight: bold; border-radius: 5px; font-size: 16px; display: inline-block;">FALAR COM O CORRETOR NO WHATSAPP</a>
                                        <p style="font-size: 12px; color: #999; margin-top: 10px;">(Abra o arquivo PDF em anexo para ver todos os detalhes)</p>
                                    </div>
                                    <table width="100%" border="0" cellspacing="0" cellpadding="20" style="margin-top: 40px; background-color: #002c5d; color: #ffffff;">
                                        <tr>
                                            <td align="center">
                                                <p style="margin: 0; font-size: 16px; font-weight: bold; color: #ffffff;">{corretor_nome.upper()}</p>
                                                <p style="margin: 5px 0 15px 0; font-size: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; color: #e30613;">Consultor Direcional</p>
                                                <p style="margin: 0; font-size: 14px;">
                                                    <span style="color: #ffffff;">WhatsApp:</span> <a href="{wa_link}" style="color: #e30613; text-decoration: none; font-weight: bold;">{corretor_tel}</a>
                                                    <span style="margin: 0 10px; color: #666;">|</span>
                                                    <span style="color: #ffffff;">Email:</span> <a href="mailto:{corretor_email}" style="color: #e30613; text-decoration: none; font-weight: bold;">{corretor_email}</a>
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
    else:
        msg["Subject"] = f"LEAD: {nome_cliente} - {emp} - {unid}"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        </head>
        <body style="font-family: 'Arial', sans-serif; color: #333; background-color: #eee; margin: 0; padding: 20px;">
            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                <tr>
                    <td align="center">
                        <table width="650" border="0" cellspacing="0" cellpadding="0" style="background-color: #fff; border: 1px solid #ccc;">
                            <tr>
                                <td align="center" style="background-color: #002c5d; padding: 20px; border-bottom: 4px solid #e30613;">
                                    <img src="{URL_LOGO_BRANCA}" width="150" style="display: block;">
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 30px;">
                                    <h3 style="color: #002c5d; border-bottom: 2px solid #e30613; padding-bottom: 10px; margin-top: 0;">RESUMO DE ATENDIMENTO</h3>
                                    <table width="100%" border="0" cellspacing="0" cellpadding="15" style="margin-bottom: 20px; background: #f9f9f9;">
                                        <tr>
                                            <td width="50%" valign="top">
                                                <p style="margin: 0 0 5px 0; font-size: 12px; color: #666;">CLIENTE</p>
                                                <p style="margin: 0; font-weight: bold; font-size: 16px;">{nome_cliente}</p>
                                                <p style="margin: 5px 0 0 0; font-size: 14px;">Renda: R$ {renda_cli}</p>
                                            </td>
                                            <td width="50%" valign="top">
                                                <p style="margin: 0 0 5px 0; font-size: 12px; color: #666;">PRODUTO</p>
                                                <p style="margin: 0; font-weight: bold; font-size: 16px;">{emp}</p>
                                                <p style="margin: 5px 0 0 0;">Unid: {unid}</p>
                                            </td>
                                        </tr>
                                    </table>
                                    <h4 style="color: #002c5d; margin-top: 0;">Valores do Imóvel</h4>
                                    <table width="100%" border="1" cellspacing="0" cellpadding="8" style="border-collapse: collapse; border-color: #ddd; margin-bottom: 20px; font-size: 14px;">
                                        <tr style="background-color: #f2f2f2;">
                                            <td>Valor Venda (VCM)</td>
                                            <td align="right" style="color: #e30613;"><b>R$ {val_venda}</b></td>
                                        </tr>
                                        <tr>
                                            <td>Avaliação Bancária</td>
                                            <td align="right">R$ {val_aval}</td>
                                        </tr>
                                    </table>
                                    <h4 style="color: #002c5d;">Plano de Pagamento</h4>
                                    <table width="100%" border="1" cellspacing="0" cellpadding="8" style="border-collapse: collapse; border-color: #ddd; margin-bottom: 20px; font-size: 14px;">
                                        <tr style="background-color: #f2f2f2;">
                                            <td>Entrada Total</td>
                                            <td align="right" style="color: #002c5d;"><b>R$ {entrada}</b></td>
                                        </tr>
                                        <tr><td>&nbsp;&nbsp;↳ Ato Imediato</td><td align="right">R$ {a0}</td></tr>
                                        <tr><td>&nbsp;&nbsp;↳ 30 Dias</td><td align="right">R$ {a30}</td></tr>
                                        <tr><td>&nbsp;&nbsp;↳ 60 Dias</td><td align="right">R$ {a60}</td></tr>
                                        <tr><td>&nbsp;&nbsp;↳ 90 Dias</td><td align="right">R$ {a90}</td></tr>
                                        <tr style="background-color: #f2f2f2;">
                                            <td>Financiamento</td>
                                            <td align="right">R$ {finan}</td>
                                        </tr>
                                        <tr>
                                            <td>Mensal Pro Soluto</td>
                                            <td align="right">R$ {ps}</td>
                                        </tr>
                                    </table>
                                    <p style="font-size: 12px; color: #999; text-align: center; margin-top: 30px;">Simulação gerada via Direcional Rio Simulador.</p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

    msg.attach(MIMEText(html_content, "html"))

    if pdf_bytes:
        part = MIMEApplication(pdf_bytes, Name=f"Resumo_{nome_cliente}.pdf")
        part["Content-Disposition"] = f'attachment; filename="Resumo_{nome_cliente}.pdf"'
        msg.attach(part)
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, destinatario, msg.as_string())
        server.quit()
        return True, "E-mail enviado com sucesso!"
    except smtplib.SMTPAuthenticationError:
        return False, "Erro de Autenticacao (535). Verifique Senha de App."
    except Exception as e:
        return False, f"Erro envio: {e}"
