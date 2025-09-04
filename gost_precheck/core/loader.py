# gost_precheck/core/loader.py
import os, zipfile, re
from typing import List, Tuple, Dict, Any, Optional
from xml.etree.ElementTree import iterparse

_EM_DASH = "—"
_EN_DASH = "–"
_HYPHEN  = "-"

def _post_normalize(text: str, cfg: Dict) -> str:
    post = cfg.get("settings", {}).get("post_normalize", {}) or \
           cfg.get("settings", {}).get("loader", {}).get("post_normalize", {}) or {}
    if post.get("dashes", False):
        text = re.sub(r"(?<=\S)\s-\s(?=\S)", f" {_EM_DASH} ", text)
        text = re.sub(r"(?<=\S)\s–\s(?=\S)", f" {_EM_DASH} ", text)
    if post.get("quotes", False):
        text = re.sub(r'(^|[\s(\[])\"', r'\1«', text)
        text = re.sub(r'\"([\s)\].,;:!?]|$)', r'»\1', text)
        text = re.sub(r'(^|[\s(\[])\'', r'\1„', text)
        text = re.sub(r'\'([\s)\].,;:!?]|$)', r'“\1', text)
    return text

def _cfg_include_styles(cfg: Dict) -> bool:
    return bool(cfg.get("settings", {}).get("loader", {}).get("include_styles", True))

def _cfg_include_tabs(cfg: Dict) -> bool:
    # Важно: если False, табы учитываются только в статистике.
    return bool(cfg.get("settings", {}).get("loader", {}).get("include_tabs", True))

_NS_ENDS = {
    "p": "}p",
    "r": "}r",
    "t": "}t",
    "pPr": "}pPr",
    "pStyle": "}pStyle",
    "instrText": "}instrText",
    "del": "}del",
    "tab": "}tab",
    "br": "}br",
}

def load_paragraphs(path: str, cfg: Dict) -> Tuple[List[str], Dict[str, Any]]:
    ext = os.path.splitext(path.lower())[1]
    if ext == ".txt":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        para_list = [p.strip() for p in re.split(r"\r?\n\s*\r?\n", text) if p.strip()]
        para_list = [_post_normalize(p, cfg) for p in para_list]
        stats = {
            "p_total": len(para_list), "kept": len(para_list), "blank": 0,
            "wt": 0, "instr": 0, "deleted": 0, "tabs": 0, "tabs_injected": 0, "br": 0, "parts": 0,
            "styles": []
        }
        return para_list, stats

    if ext != ".docx":
        raise RuntimeError("Поддерживаются только .txt и .docx")

    return _iter_docx_paragraphs(path, cfg)

def _iter_docx_paragraphs(path: str, cfg: Dict) -> Tuple[List[str], Dict[str, Any]]:
    keep_styles_meta = _cfg_include_styles(cfg)
    inject_tabs      = _cfg_include_tabs(cfg)

    p_total = kept = blank = wt = instr = deleted = tabs = br = tabs_injected = 0
    styles_by_idx: List[Optional[str]] = []

    paras: List[str] = []
    cur_text_parts: List[str] = []
    cur_style: Optional[str] = None

    with zipfile.ZipFile(path) as z:
        with z.open("word/document.xml") as f:
            for event, elem in iterparse(f, events=("end",)):
                tag = elem.tag

                if tag.endswith(_NS_ENDS["p"]):
                    p_total += 1
                    para = "".join(cur_text_parts).strip()
                    if not para:
                        blank += 1
                    else:
                        kept += 1
                        para = _post_normalize(para, cfg)
                        paras.append(para)
                        styles_by_idx.append(cur_style if keep_styles_meta else None)
                    cur_text_parts.clear()
                    cur_style = None
                    elem.clear()
                    continue

                if tag.endswith(_NS_ENDS["pStyle"]):
                    val = elem.attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val")
                    if val:
                        cur_style = val
                    elem.clear()
                    continue

                if tag.endswith(_NS_ENDS["del"]):
                    deleted += 1
                    elem.clear()
                    continue

                if tag.endswith(_NS_ENDS["instrText"]):
                    instr += 1
                    elem.clear()
                    continue

                if tag.endswith(_NS_ENDS["tab"]):
                    tabs += 1
                    if inject_tabs:
                        cur_text_parts.append("\t")
                        tabs_injected += 1
                    elem.clear()
                    continue

                if tag.endswith(_NS_ENDS["br"]):
                    br += 1
                    # перенос строки в пределах абзаца — не добавляем явный '\n' (оставим как есть)
                    elem.clear()
                    continue

                if tag.endswith(_NS_ENDS["t"]):
                    text = elem.text or ""
                    if text:
                        wt += 1
                        cur_text_parts.append(text)
                    elem.clear()
                    continue

                elem.clear()

    stats = {
        "p_total": p_total, "kept": kept, "blank": blank,
        "wt": wt, "instr": instr, "deleted": deleted, "tabs": tabs, "tabs_injected": tabs_injected, "br": br,
        "parts": 0,
        "styles": styles_by_idx,
    }
    return paras, stats

def load_paragraphs_from_ooxml(ooxml: str, cfg: Dict) -> Tuple[List[str], Dict[str, Any], List[Dict]]:
    """
    Разбирает строку OOXML (как в word/document.xml), возвращает:
    - paragraphs: List[str]
    - stats: {...}
    - spans: List[{"para_index": i, "start": off0, "end": off1}] — глобальные смещения в конкатенированном тексте
      (можно не использовать сразу; пригодится для точной подсветки)
    """
    paras, stats = [], {"p_total":0, "kept":0, "blank":0, "wt":0, "instr":0, "deleted":0, "tabs":0, "br":0, "parts":0, "styles":[]}
    spans = []
    cur = []
    total_offset = 0
    buf = io.BytesIO(ooxml.encode("utf-8"))
    for ev, elem in iterparse(buf, events=("end",)):
        tag = elem.tag
        if tag.endswith("}p"):
            stats["p_total"] += 1
            s = "".join(cur).strip()
            if s:
                paras.append(s)
                stats["kept"] += 1
                spans.append({"para_index": len(paras)-1, "start": total_offset, "end": total_offset + len(s)})
                total_offset += len(s) + 1  # \n между абзацами
            else:
                stats["blank"] += 1
            cur.clear()
            elem.clear()
            continue
        if tag.endswith("}t"):
            t = elem.text or ""
            if t:
                stats["wt"] += 1
                cur.append(t)
            elem.clear()
            continue
        elem.clear()
    return paras, stats, spans