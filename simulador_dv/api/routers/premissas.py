# -*- coding: utf-8 -*-
from fastapi import APIRouter

from simulador_dv.data.premissas import DEFAULT_PREMISSAS

router = APIRouter(tags=["premissas"])


@router.get("/premissas/default")
def premissas_default() -> dict:
    return dict(DEFAULT_PREMISSAS)
