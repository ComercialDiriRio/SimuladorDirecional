# -*- coding: utf-8 -*-
"""Catálogo da galeria (paridade com `CATALOGO_PRODUTOS` + JSON em `app.py`)."""
from __future__ import annotations

import copy
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from simulador_dv.services.format_utils import fmt_br
from simulador_dv.services.home_banners import cms_content_cache_ttl_sec

logger = logging.getLogger(__name__)

_RESERVED_KEYS = frozenset({"__removidos", "__extras"})

_catalogo_merged_t: float = 0.0
_catalogo_merged_data: Optional[Dict[str, Any]] = None


def invalidate_catalogo_merged_cache() -> None:
    global _catalogo_merged_t, _catalogo_merged_data
    _catalogo_merged_t = 0.0
    _catalogo_merged_data = None


def _paths_catalogo_json() -> List[Path]:
    here = Path(__file__).resolve().parents[1]  # simulador_dv/
    root = here.parent
    return [
        root / "static" / "img" / "galeria" / "catalogo_produtos.json",
        root / "catalogo_produtos.json",
        here / "static" / "img" / "galeria" / "catalogo_produtos.json",
    ]


def load_catalogo_produtos_from_json() -> Dict[str, Any]:
    """Sobrescreve/define catálogo a partir dos mesmos ficheiros que `app.py`."""
    for p in _paths_catalogo_json():
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except Exception:
                continue
    return {}


_OVERRIDES_PATH = Path(__file__).resolve().parents[1] / "data" / "galeria_overrides.json"


def _load_overrides_raw() -> Dict[str, Any]:
    if _OVERRIDES_PATH.is_file():
        try:
            with open(_OVERRIDES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.warning("galeria_overrides: %s", e)
    return {}


def _save_overrides_raw(data: Dict[str, Any]) -> None:
    _OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_OVERRIDES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _split_overrides(ov: Dict[str, Any]) -> Tuple[Set[str], Dict[str, Any], Dict[str, Any]]:
    """Devolve (removidos, extras, patches). Formato legado: só patches."""
    raw_r = ov.get("__removidos")
    removidos: Set[str] = set()
    if isinstance(raw_r, list):
        removidos = {str(x).strip() for x in raw_r if str(x).strip()}
    extras_raw = ov.get("__extras")
    extras: Dict[str, Any] = {}
    if isinstance(extras_raw, dict):
        for k, v in extras_raw.items():
            ks = str(k).strip()
            if ks and isinstance(v, dict):
                extras[ks] = copy.deepcopy(v)
    patches: Dict[str, Any] = {}
    for k, v in ov.items():
        if k in _RESERVED_KEYS:
            continue
        if isinstance(v, dict):
            patches[str(k).strip()] = copy.deepcopy(v)
    return removidos, extras, patches


def _build_overrides_file(removidos: Set[str], extras: Dict[str, Any], patches: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = dict(patches)
    if removidos:
        out["__removidos"] = sorted(removidos)
    if extras:
        out["__extras"] = {k: copy.deepcopy(v) for k, v in sorted(extras.items())}
    return out


def _save_overrides_from_parts(removidos: Set[str], extras: Dict[str, Any], patches: Dict[str, Any]) -> None:
    _save_overrides_raw(_build_overrides_file(removidos, extras, patches))


def _merge_um_produto(base_meta: Any, override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    out = copy.deepcopy(base_meta) if isinstance(base_meta, dict) else {}
    if not override:
        return out
    if "video" in override:
        out["video"] = override["video"]
    if "imagens" in override and isinstance(override["imagens"], list):
        out["imagens"] = copy.deepcopy(override["imagens"])
    if "lat" in override and override["lat"] is not None:
        try:
            out["lat"] = float(override["lat"])
        except (TypeError, ValueError):
            pass
    if "lon" in override and override["lon"] is not None:
        try:
            out["lon"] = float(override["lon"])
        except (TypeError, ValueError):
            pass
    return out


def _sanitizar_imagens_lista(imagens: Any) -> List[Dict[str, str]]:
    limpa: List[Dict[str, str]] = []
    if not isinstance(imagens, list):
        return limpa
    for it in imagens:
        if not isinstance(it, dict):
            continue
        nm = str(it.get("nome", "")).strip()
        lk = str(it.get("link", "")).strip()
        if nm or lk:
            limpa.append({"nome": nm, "link": lk})
    return limpa


def _merge_catalogo(
    base: Dict[str, Any],
    removidos: Set[str],
    extras: Dict[str, Any],
    patches: Dict[str, Any],
) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for nome, meta in base.items():
        if nome in removidos:
            continue
        merged[nome] = _merge_um_produto(meta, patches.get(nome) if isinstance(patches.get(nome), dict) else None)
    for nome, meta in extras.items():
        if nome in removidos:
            continue
        merged[nome] = copy.deepcopy(meta) if isinstance(meta, dict) else {}
    return merged


def _maybe_sync_galeria_sheet(nome: str, meta: Optional[Dict[str, Any]] = None, *, delete: bool = False) -> None:
    try:
        from simulador_dv.services import sheets_cms

        if delete:
            sheets_cms.delete_galeria_empreendimento_row(nome)
        elif meta is not None:
            sheets_cms.upsert_galeria_empreendimento_row(nome, meta)
    except Exception as e:
        logger.warning("Sincronização BD Galeria Empreendimentos: %s", e)


def load_catalogo_merged() -> Dict[str, Any]:
    """Catálogo base + overrides; depois camada BD Galeria Empreendimentos (Sheets), se existir."""
    global _catalogo_merged_t, _catalogo_merged_data
    now = time.monotonic()
    if _catalogo_merged_data is not None and (now - _catalogo_merged_t) < cms_content_cache_ttl_sec():
        return _catalogo_merged_data

    base = load_catalogo_produtos_from_json()
    ov = _load_overrides_raw()
    removidos, extras, patches = _split_overrides(ov)
    merged = _merge_catalogo(base, removidos, extras, patches)
    try:
        from simulador_dv.services import sheets_cms

        sheet_cat = sheets_cms.load_galeria_empreendimentos_catalog()
        if sheet_cat:
            for nome, sm in sheet_cat.items():
                if nome in removidos:
                    continue
                cur = merged.get(nome)
                cur_d = cur if isinstance(cur, dict) else {}
                merged[nome] = _merge_um_produto(cur_d, sm if isinstance(sm, dict) else None)
    except Exception as e:
        logger.debug("Catálogo galeria + Sheets: %s", e)
    _catalogo_merged_data = merged
    _catalogo_merged_t = now
    return merged


def lista_produtos_ordenada(catalogo: Dict[str, Any]) -> List[str]:
    return sorted(catalogo.keys())


def aplicar_patch_galeria_admin(nome_produto: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Atualiza vídeo/imagens/lat/lon. Produto base → patches; produto só em extras → atualiza extras.
    """
    base = load_catalogo_produtos_from_json()
    raw = _load_overrides_raw()
    removidos, extras, patches = _split_overrides(raw)
    nome = nome_produto.strip()
    merged = _merge_catalogo(base, removidos, extras, patches)
    if nome not in merged:
        raise ValueError("Empreendimento não existe no catálogo")

    if nome in extras:
        meta = copy.deepcopy(extras[nome])
    else:
        meta = _merge_um_produto(base[nome], patches.get(nome) if isinstance(patches.get(nome), dict) else None)

    if "video" in patch:
        meta["video"] = patch["video"]
    if "imagens" in patch:
        meta["imagens"] = _sanitizar_imagens_lista(patch["imagens"])
    if "lat" in patch:
        if patch["lat"] is None:
            meta.pop("lat", None)
        else:
            try:
                meta["lat"] = float(patch["lat"])
            except (TypeError, ValueError):
                pass
    if "lon" in patch:
        if patch["lon"] is None:
            meta.pop("lon", None)
        else:
            try:
                meta["lon"] = float(patch["lon"])
            except (TypeError, ValueError):
                pass

    if nome in extras:
        extras[nome] = meta
    else:
        cur_p = dict(patches.get(nome) or {}) if isinstance(patches.get(nome), dict) else {}
        if "video" in patch:
            cur_p["video"] = meta.get("video", "")
        if "imagens" in patch:
            cur_p["imagens"] = meta.get("imagens", [])
        if "lat" in patch:
            if patch["lat"] is None:
                cur_p.pop("lat", None)
            elif "lat" in meta:
                cur_p["lat"] = meta["lat"]
        if "lon" in patch:
            if patch["lon"] is None:
                cur_p.pop("lon", None)
            elif "lon" in meta:
                cur_p["lon"] = meta["lon"]
        patches[nome] = cur_p

    _save_overrides_from_parts(removidos, extras, patches)
    # Gravar na planilha o meta pós-patch (JSON); evita sheet antiga sobrescrever antes do upsert.
    _maybe_sync_galeria_sheet(nome, copy.deepcopy(meta))
    invalidate_catalogo_merged_cache()
    return load_catalogo_merged().get(nome, meta)


def criar_empreendimento_galeria_admin(nome: str, meta_in: Dict[str, Any]) -> Dict[str, Any]:
    """Novo empreendimento apenas em __extras (não altera catalogo_produtos.json)."""
    nome = nome.strip()
    if not nome:
        raise ValueError("Nome do empreendimento é obrigatório")

    base = load_catalogo_produtos_from_json()
    raw = _load_overrides_raw()
    removidos, extras, patches = _split_overrides(raw)
    merged = _merge_catalogo(base, removidos, extras, patches)
    if nome in merged:
        raise ValueError("Já existe um empreendimento com este nome no catálogo")

    meta: Dict[str, Any] = {
        "video": str(meta_in.get("video") or "").strip(),
        "imagens": _sanitizar_imagens_lista(meta_in.get("imagens")),
    }
    if meta_in.get("lat") is not None:
        try:
            meta["lat"] = float(meta_in["lat"])
        except (TypeError, ValueError):
            pass
    if meta_in.get("lon") is not None:
        try:
            meta["lon"] = float(meta_in["lon"])
        except (TypeError, ValueError):
            pass

    extras[nome] = meta
    _save_overrides_from_parts(removidos, extras, patches)
    _maybe_sync_galeria_sheet(nome, copy.deepcopy(meta))
    return copy.deepcopy(meta)


def excluir_empreendimento_galeria_admin(nome: str) -> None:
    """Remove extra ADM ou oculta entrada do catálogo base (__removidos)."""
    nome = nome.strip()
    if not nome:
        raise ValueError("Nome inválido")

    base = load_catalogo_produtos_from_json()
    raw = _load_overrides_raw()
    removidos, extras, patches = _split_overrides(raw)

    if nome in extras:
        del extras[nome]
        _save_overrides_from_parts(removidos, extras, patches)
        _maybe_sync_galeria_sheet(nome, delete=True)
        invalidate_catalogo_merged_cache()
        return
    if nome in base:
        removidos.add(nome)
        patches.pop(nome, None)
        _save_overrides_from_parts(removidos, extras, patches)
        _maybe_sync_galeria_sheet(nome, delete=True)
        invalidate_catalogo_merged_cache()
        return
    raise ValueError("Empreendimento não encontrado no catálogo")


_PREFIXOS_EMP_NORM = ("CONQUISTA ", "RESERVA ", "LA VIE ", "LIFE ")


def _chave_normalizada_empreendimento(nome: str) -> str:
    u = str(nome or "").strip().upper()
    for p in _PREFIXOS_EMP_NORM:
        if u.startswith(p):
            u = u[len(p) :].strip()
    return u


def _df_estoque_filtrado_por_empreendimento(df_estoque: pd.DataFrame, nome_empreendimento: str) -> pd.DataFrame:
    col = df_estoque["Empreendimento"].astype(str).str.strip().str.upper()
    key = nome_empreendimento.strip().upper()
    m = col == key
    if not m.any():
        nk = _chave_normalizada_empreendimento(nome_empreendimento)
        m = col.map(_chave_normalizada_empreendimento) == nk
    if not m.any() and nk:
        m = col.str.contains(re.escape(nk), case=False, na=False)
    return df_estoque[m]


def metricas_empreendimento_estoque(
    nome_empreendimento: str,
    df_estoque: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Mesmos números que o bloco da galeria no Streamlit (~L980–L1026 de app.py).
    """
    out: Dict[str, Any] = {
        "empreendimento": nome_empreendimento,
        "variacao_preco": None,
        "metragem": None,
        "preco_m2": None,
        "entrega": None,
        "blocos_unidades": None,
        "bairro": None,
        "endereco": None,
        "num_unidades": 0,
    }
    if df_estoque.empty or "Empreendimento" not in df_estoque.columns:
        return out
    df_emp = _df_estoque_filtrado_por_empreendimento(df_estoque, nome_empreendimento)
    if df_emp.empty:
        logger.warning(
            "metricas_empreendimento_estoque: nenhuma unidade para %r (estoque tem %d linhas)",
            nome_empreendimento,
            len(df_estoque),
        )
        return out
    min_p = float(df_emp["Valor de Venda"].min())
    max_p = float(df_emp["Valor de Venda"].max())
    out["variacao_preco"] = f"R$ {fmt_br(min_p)} a R$ {fmt_br(max_p)}"
    areas_vals = pd.to_numeric(df_emp["Area"], errors="coerce").dropna() if "Area" in df_emp.columns else pd.Series(dtype=float)
    if not areas_vals.empty:
        min_area = float(areas_vals.min())
        max_area = float(areas_vals.max())
        out["metragem"] = f"{min_area}m² a {max_area}m²"
        min_m2 = min_p / max_area if max_area > 0 else 0
        max_m2 = max_p / min_area if min_area > 0 else 0
        out["preco_m2"] = f"R$ {fmt_br(min_m2)} a R$ {fmt_br(max_m2)}"
    else:
        out["metragem"] = "N/A"
        out["preco_m2"] = "N/A"
    num_unidades = len(df_emp)
    num_blocos = int(df_emp["Bloco_Sort"].nunique()) if "Bloco_Sort" in df_emp.columns else 1
    out["num_unidades"] = num_unidades
    out["blocos_unidades"] = f"{num_blocos} / {num_unidades}"
    out["bairro"] = str(df_emp["Bairro"].iloc[0]) if "Bairro" in df_emp.columns else "N/A"
    out["endereco"] = str(df_emp["Endereco"].iloc[0]) if "Endereco" in df_emp.columns else "N/A"
    out["entrega"] = str(df_emp["Data Entrega"].iloc[0]) if "Data Entrega" in df_emp.columns else "N/A"
    return out
