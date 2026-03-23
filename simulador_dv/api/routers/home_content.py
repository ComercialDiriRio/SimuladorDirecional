# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Annotated, Any, Dict, List

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from simulador_dv.api.deps import require_admin, require_session_state
from simulador_dv.services.home_banners import load_home_banners, save_home_banners

router = APIRouter(prefix="/home", tags=["home"])


class HomeBannersOut(BaseModel):
    imagens: List[str]
    is_admin: bool


class HomeBannersPutIn(BaseModel):
    imagens: List[str] = Field(default_factory=list, description="URLs das imagens de fundo, na ordem do carrossel")


@router.get("/banners")
def get_home_banners(st: dict = Depends(require_session_state)):
    _ = st["_session_id"]
    body = {
        "imagens": load_home_banners(),
        "is_admin": bool(st.get("is_admin")),
    }
    return JSONResponse(
        content=body,
        headers={"Cache-Control": "private, max-age=60"},
    )


@router.put("/banners")
def put_home_banners(
    body: HomeBannersPutIn,
    st: Annotated[dict, Depends(require_admin)],
) -> Dict[str, Any]:
    _ = st["_session_id"]
    limpa = save_home_banners(body.imagens)
    return {"ok": True, "imagens": limpa}
