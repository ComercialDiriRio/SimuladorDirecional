# -*- coding: utf-8 -*-
"""
Autenticação inicial: validação contra dados carregados ou modo demo (DEV).
Integração completa com BD Logins quando `data_loader` tiver DataFrame de logins.
"""
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request, Response

from simulador_dv.api.schemas import LoginIn, LoginOut
from simulador_dv.api.session_store import SESSION_COOKIE_NAME, create_session, delete_session
from simulador_dv.api.deps import resolve_session_id

router = APIRouter(tags=["auth"])


def _is_production_mode() -> bool:
    """Produção: desativa login demo quando SIMULADOR_PRODUCTION=1."""
    return os.environ.get("SIMULADOR_PRODUCTION", "").lower() in ("1", "true", "yes")


def _get_logins_df():
    """Prioriza leitura só da aba BD Logins; fallback para cache completo do sistema."""
    try:
        from simulador_dv.services.sistema_data import load_logins_df_only, load_sistema_dataframes

        df = load_logins_df_only()
        if df is not None and not df.empty:
            return df
        result = load_sistema_dataframes()
        return result[3] if result is not None else None
    except Exception:
        return None


def _set_session_cookie(response: Response, email: str, extra=None) -> str:
    sid = create_session(email=email, extra=extra)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=sid,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
        path="/",
    )
    return sid


@router.post("/auth/login", response_model=LoginOut)
def login(body: LoginIn, response: Response) -> LoginOut:
    email = (body.email or "").strip().lower()
    pwd = (body.password or "").strip()

    demo_env = os.environ.get("SIMULADOR_API_DEMO", "").lower() in ("1", "true", "yes")
    if demo_env and not _is_production_mode():
        if email == "demo@direcional.local" and pwd == "demo":
            sid = _set_session_cookie(
                response,
                email,
                {
                    "user_name": "Demo",
                    "user_phone": "",
                    "user_imobiliaria": "Geral",
                    "user_cargo": "Demo",
                },
            )
            return LoginOut(ok=True, message="demo", session_id=sid)

    df = _get_logins_df()
    if df is None or df.empty:
        raise HTTPException(
            status_code=503,
            detail="Base de usuários não disponível. Verifique as credenciais do Google Sheets.",
        )

    if "Email" not in df.columns or "Senha" not in df.columns:
        raise HTTPException(status_code=503, detail="Formato de logins inválido.")

    match = df[(df["Email"].astype(str).str.lower() == email) & (df["Senha"].astype(str) == pwd)]
    if match.empty:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    row = match.iloc[0]
    adm_val = str(row.get("ADM?", "")).strip().upper()
    is_admin = adm_val in ("SIM", "S", "YES", "TRUE", "1")
    extra = {
        "user_name": str(row.get("Nome", "")).strip(),
        "user_phone": str(row.get("Telefone", "")).strip(),
        "user_imobiliaria": str(row.get("Imobiliaria", "Geral")).strip(),
        "user_cargo": str(row.get("Cargo", "")).strip(),
        "is_admin": is_admin,
    }
    sid = _set_session_cookie(response, email, extra)
    return LoginOut(ok=True, message="ok", session_id=sid)


@router.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id"),
) -> dict:
    sid = resolve_session_id(request, x_session_id)
    if sid:
        delete_session(sid)
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"ok": True}
