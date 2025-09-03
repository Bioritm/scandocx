# gost_precheck/core/loader.py
import os, zipfile, re
from typing import List, Tuple, Dict, Any
from xml.etree.ElementTree import iterparse

def _post_normalize(text: str, cfg: Dict) -> str:
    pn = cfg.get("settings", {}).get("post_normalize", {})
    if not pn:
        return text

    # Нормализация тире: приводим все U+2010..2015 к однородной форме (без замены '-' на '—', чтобы не скрывать ошибки)
    if pn.get("dashes", False):
        text = (text
                .replace("\u2010", "-") # hyphen
                .replace("\u2011", "-") # non-breaking hyphen
                .replace("\u2012", "-") # figure dash
                .replace("\u2013", "-") # en dash
                .replace("\u2212", "-") # minus
                .replace("\u2014", "—") # em dash оставляем типографское тире
                .replace("\u2015", "—"))

    # Нормализация кавычек: конвертируем экзотику к базовым «», „“
    if pn.get("quotes", False):
        # прямые кавычки в «»
        text = text.replace('"', '«').replace("'", "’")
        # варианты в типографские
        text = (text
                .replace("”", "»").replace("“", "«")
                .replace("„", "„").replace("‚", "‚")
                .replace("« ", "«").replace(" »", "»"))

    return text

def load_paragraphs(path: str, cfg: Dict) -> Tuple[List[str], Dict[str, Any]]:
    ext = os.path.splitext(path.lower())[1]
    stats: Dict[str, Any] = {
        "p_total": 0, "kept": 0, "blank": 0, "wt": 0, "instr": 0, "deleted": 0,
        "tabs": 0, "br": 0, "parts": 0, "styles": []
    }

    if ext == ".txt":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
        parts = [p.strip() for p in re.split(r"\r?\n\s*\r?\n", raw)]
        stats["p_total"] = len(parts)
        kept = []
        for p in parts:
            if not p:
                stats["blank"] += 1
                continue
            p2 = _post_normalize(p, cfg)
            kept.append(p2)
        stats["kept"] = len(kept)
        return kept, stats

    if ext != ".docx":
        raise RuntimeError("Поддерживаются только .txt и .docx")

    paras: List[str] = []
    styles: List[str] = []
    wt = instr = deleted = tabs = br = 0

    with zipfile.ZipFile(path) as z:
        with z.open("word/document.xml") as f:
            # Потоковый парсинг, собираем текст в пределах w:p
            current_style = ""
            texts: List[str] = []

            for event, elem in iterparse(f, events=("end",)):
                tag = elem.tag
                if tag.endswith('}pPr'):  # свойства параграфа
                    for st in elem:
                        if st.tag.endswith('}pStyle'):
                            val = st.attrib.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', '')
                            current_style = val or ""
                elif tag.endswith('}t'):
                    wt += 1
                    if elem.text:
                        texts.append(elem.text)
                elif tag.endswith('}instrText'):
                    instr += 1
                elif tag.endswith('}delText'):
                    deleted += 1
                elif tag.endswith('}tab'):
                    tabs += 1
                elif tag.endswith('}br'):
                    br += 1
                elif tag.endswith('}p'):
                    stats["p_total"] += 1
                    para = "".join(texts).strip()
                    styles.append(current_style)
                    if not para:
                        stats["blank"] += 1
                    else:
                        para = _post_normalize(para, cfg)
                        paras.append(para)
                    # reset
                    texts.clear()
                    current_style = ""
                    elem.clear()
                else:
                    elem.clear()

    stats["wt"], stats["instr"], stats["deleted"], stats["tabs"], stats["br"] = wt, instr, deleted, tabs, br
    stats["kept"] = len(paras)
    stats["styles"] = styles
    return paras, stats
