# -*- coding: utf-8 -*-
"""
Conteúdo editorial em Google Sheets: BD Home, BD Galeria Empreendimentos, BD Galeria Mídias.
Desativar com env DISABLE_SHEETS_CMS=1 (usa só JSON local).
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

import pandas as pd

from simulador_dv.services.sistema_data import _open_spreadsheet_gspread

logger = logging.getLogger(__name__)

WS_HOME = "BD Home"
WS_GAL_EMP = "BD Galeria Empreendimentos"
WS_GAL_MID = "BD Galeria Mídias"

_GAL_HEADER = [
    "Empreendimento",
    "Video_URL",
    "Latitude",
    "Longitude",
    "Imagens_JSON",
    "Ficha_PDF",
    "Ativo",
    "Ordem",
]

_CONTEUDO_HEADER = [
    "Id",
    "Tipo",
    "Titulo",
    "Descricao",
    "Imagem",
    "Data",
    "Video_URL",
    "Ordem",
    "Imagens_Drive_JSON",
    "Pdfs_JSON",
]


def cms_disabled() -> bool:
    return os.environ.get("DISABLE_SHEETS_CMS", "").strip().lower() in ("1", "true", "yes")


def _get_ws(title: str):
    if cms_disabled():
        return None
    sh = _open_spreadsheet_gspread()
    if sh is None:
        return None
    try:
        return sh.worksheet(title)
    except Exception as e:
        logger.debug("worksheet %r: %s", title, e)
        return None


def _ativo_val(v: Any) -> bool:
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
        return True
    s = str(v).strip().lower()
    if s in ("não", "nao", "n", "false", "0", "não"):
        return False
    return True


def home_banners_from_sheet() -> Optional[List[str]]:
    ws = _get_ws(WS_HOME)
    if ws is None:
        return None
    try:
        records = ws.get_all_records()
    except Exception as e:
        logger.warning("BD Home leitura: %s", e)
        return None
    if not records:
        return None
    df = pd.DataFrame(records)
    if df.empty:
        return None
    url_col = None
    for c in df.columns:
        lu = str(c).strip().lower()
        if "url_imagem" == lu or lu == "imagem":
            url_col = c
            break
        if "url" in lu and "imagem" in lu:
            url_col = c
            break
    if url_col is None:
        for c in df.columns:
            if "url" in str(c).lower():
                url_col = c
                break
    if url_col is None:
        return None
    ord_col = next((c for c in df.columns if "ordem" in str(c).lower()), None)
    ativo_col = next((c for c in df.columns if str(c).strip().lower() == "ativo"), None)
    sub = df
    if ativo_col and ativo_col in df.columns:
        sub = sub[sub[ativo_col].map(_ativo_val)]
    if sub.empty:
        return None
    if ord_col and ord_col in sub.columns:
        sub = sub.copy()
        sub["_ord"] = pd.to_numeric(sub[ord_col], errors="coerce").fillna(9999)
        sub = sub.sort_values("_ord")
    urls = [str(x).strip() for x in sub[url_col].tolist() if str(x).strip()]
    return urls or None


def home_banners_save_sheet(urls: List[str]) -> bool:
    ws = _get_ws(WS_HOME)
    if ws is None:
        return False
    try:
        header = ["Ordem", "URL_Imagem", "Titulo", "Ativo"]
        body = [[i + 1, u, "", "Sim"] for i, u in enumerate(urls)]
        ws.clear()
        ws.update("A1", [header] + body, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        logger.warning("BD Home gravação: %s", e)
        return False


def _parse_imagens_json(raw: Any) -> List[Dict[str, str]]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return []
    s = str(raw).strip()
    if not s:
        return []
    try:
        j = json.loads(s)
        if isinstance(j, dict):
            return [{"nome": str(k), "link": str(v)} for k, v in j.items() if str(v).strip()]
        if isinstance(j, list):
            out: List[Dict[str, str]] = []
            for it in j:
                if isinstance(it, dict):
                    nm = str(it.get("nome", "")).strip()
                    lk = str(it.get("link", "")).strip()
                    if lk:
                        out.append({"nome": nm, "link": lk})
            return out
    except json.JSONDecodeError:
        pass
    return []


def load_galeria_empreendimentos_catalog() -> Optional[Dict[str, Any]]:
    ws = _get_ws(WS_GAL_EMP)
    if ws is None:
        return None
    try:
        records = ws.get_all_records()
    except Exception as e:
        logger.debug("BD Galeria Empreendimentos: %s", e)
        return None
    if not records:
        return None
    out: Dict[str, Any] = {}
    for r in records:
        nome = str(r.get("Empreendimento") or r.get("Nome_Exibicao") or r.get("Nome") or "").strip()
        if not nome:
            continue
        if not _ativo_val(r.get("Ativo")):
            continue
        video = str(r.get("Video_URL") or r.get("Video") or "").strip()
        imagens = _parse_imagens_json(r.get("Imagens_JSON") or r.get("Imagens_json") or r.get("Imagens"))
        meta: Dict[str, Any] = {"video": video, "imagens": imagens}
        for src, dst in [("Latitude", "lat"), ("Longitude", "lon"), ("Lat", "lat"), ("Lon", "lon")]:
            if src in r and r[src] not in (None, ""):
                try:
                    meta[dst] = float(str(r[src]).replace(",", "."))
                except (TypeError, ValueError):
                    pass
        pdf = str(r.get("Ficha_PDF") or r.get("Link_PDF") or "").strip()
        if pdf:
            imgs = list(meta.get("imagens") or [])
            imgs.append({"nome": "Ficha técnica (PDF)", "link": pdf})
            meta["imagens"] = imgs
        out[nome] = meta
    return out or None


def _meta_to_galeria_row(nome: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    imagens_dict: Dict[str, str] = {}
    for it in meta.get("imagens") or []:
        if isinstance(it, dict):
            nm = str(it.get("nome", "")).strip()
            lk = str(it.get("link", "")).strip()
            if nm and lk and "ficha" not in nm.lower() and "pdf" not in nm.lower():
                imagens_dict[nm] = lk
    ficha = ""
    for it in meta.get("imagens") or []:
        if isinstance(it, dict):
            nm = (it.get("nome") or "").lower()
            lk = str(it.get("link", "") or "").strip()
            if lk and ("ficha" in nm or "pdf" in nm or "book" in nm):
                ficha = lk
                break
    lat = meta.get("lat")
    lon = meta.get("lon")
    return {
        "Empreendimento": nome,
        "Video_URL": str(meta.get("video") or ""),
        "Latitude": "" if lat is None else lat,
        "Longitude": "" if lon is None else lon,
        "Imagens_JSON": json.dumps(imagens_dict, ensure_ascii=False) if imagens_dict else "",
        "Ficha_PDF": ficha,
        "Ativo": "Sim",
        "Ordem": meta.get("ordem", "") or "",
    }


def upsert_galeria_empreendimento_row(nome: str, meta: Dict[str, Any]) -> bool:
    ws = _get_ws(WS_GAL_EMP)
    if ws is None:
        return False
    nome = nome.strip()
    if not nome:
        return False
    try:
        records = ws.get_all_records()
    except Exception:
        records = []
    df = pd.DataFrame(records) if records else pd.DataFrame()
    for c in _GAL_HEADER:
        if c not in df.columns:
            df[c] = None
    row_data = _meta_to_galeria_row(nome, meta)
    key_col = "Empreendimento"
    if key_col not in df.columns:
        df[key_col] = ""
    mask = df[key_col].astype(str).str.strip().str.upper() == nome.upper()
    if mask.any():
        idx = df.index[mask][0]
        for k, v in row_data.items():
            df.at[idx, k] = v
    else:
        df = pd.concat([df, pd.DataFrame([row_data])], ignore_index=True)
    for c in _GAL_HEADER:
        if c not in df.columns:
            df[c] = ""
    df_out = df[_GAL_HEADER]
    body = [_GAL_HEADER]
    for _, row in df_out.iterrows():
        body.append([_cell_sheet(row[c]) for c in _GAL_HEADER])
    ws.clear()
    ws.update("A1", body, value_input_option="USER_ENTERED")
    return True


def delete_galeria_empreendimento_row(nome: str) -> bool:
    ws = _get_ws(WS_GAL_EMP)
    if ws is None:
        return False
    nome = nome.strip()
    try:
        records = ws.get_all_records()
    except Exception:
        return False
    df = pd.DataFrame(records) if records else pd.DataFrame()
    if df.empty or "Empreendimento" not in df.columns:
        ws.clear()
        ws.update("A1", [_GAL_HEADER], value_input_option="USER_ENTERED")
        return True
    df = df[df["Empreendimento"].astype(str).str.strip().str.upper() != nome.upper()]
    for c in _GAL_HEADER:
        if c not in df.columns:
            df[c] = ""
    df_out = df[_GAL_HEADER]
    body = [_GAL_HEADER]
    for _, row in df_out.iterrows():
        body.append([_cell_sheet(row[c]) for c in _GAL_HEADER])
    ws.clear()
    ws.update("A1", body, value_input_option="USER_ENTERED")
    return True


def _cell_sheet(v: Any) -> Any:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return v


def _item_to_conteudo_row(tipo_label: str, it: Dict[str, Any]) -> List[Any]:
    return [
        it.get("id", ""),
        tipo_label,
        it.get("titulo", ""),
        it.get("descricao", ""),
        it.get("imagem", ""),
        it.get("data", ""),
        it.get("video_url", ""),
        it.get("ordem", "") or "",
        json.dumps(it.get("imagens_drive") or [], ensure_ascii=False),
        json.dumps(it.get("pdfs") or [], ensure_ascii=False),
    ]


def _loads_json_list_cell(raw: Any) -> List[Dict[str, Any]]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return []
    try:
        j = json.loads(str(raw)) if not isinstance(raw, (list, dict)) else raw
        return j if isinstance(j, list) else []
    except json.JSONDecodeError:
        return []


def conteudo_from_sheet() -> Optional[Dict[str, List[Dict[str, Any]]]]:
    ws = _get_ws(WS_GAL_MID)
    if ws is None:
        return None
    try:
        records = ws.get_all_records()
    except Exception as e:
        logger.debug("BD Galeria Mídias: %s", e)
        return None
    if not records:
        return None
    campanhas: List[Dict[str, Any]] = []
    treinamentos: List[Dict[str, Any]] = []
    for r in records:
        tipo_raw = str(r.get("Tipo") or "").strip().lower()
        bucket = treinamentos if "treina" in tipo_raw else campanhas
        item = {
            "id": str(r.get("Id") or r.get("id") or "").strip() or f"id-{uuid.uuid4().hex[:10]}",
            "titulo": str(r.get("Titulo") or ""),
            "descricao": str(r.get("Descricao") or ""),
            "imagem": str(r.get("Imagem") or ""),
            "data": str(r.get("Data") or ""),
            "video_url": str(r.get("Video_URL") or ""),
            "imagens_drive": _loads_json_list_cell(r.get("Imagens_Drive_JSON")),
            "pdfs": _loads_json_list_cell(r.get("Pdfs_JSON")),
        }
        if "ordem" in r and r["ordem"] not in (None, ""):
            try:
                item["ordem"] = int(float(str(r["ordem"]).replace(",", ".")))
            except (TypeError, ValueError):
                pass
        bucket.append(item)
    if not campanhas and not treinamentos:
        return None
    return {"campanhas": campanhas, "treinamentos": treinamentos}


def conteudo_save_full(data: Dict[str, List[Dict[str, Any]]]) -> bool:
    ws = _get_ws(WS_GAL_MID)
    if ws is None:
        return False
    rows: List[List[Any]] = []
    for it in data.get("campanhas") or []:
        rows.append(_item_to_conteudo_row("campanha", it))
    for it in data.get("treinamentos") or []:
        rows.append(_item_to_conteudo_row("treinamento", it))
    try:
        body = [_CONTEUDO_HEADER] + rows
        ws.clear()
        ws.update("A1", body, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        logger.warning("BD Galeria Mídias gravação: %s", e)
        return False
