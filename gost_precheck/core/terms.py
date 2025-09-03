# gost_precheck/core/terms.py
from __future__ import annotations
from typing import Dict, List, Iterable
import re, json, csv, os
from .loader import load_paragraphs

# АКРОНИМЫ: 2+ заглавных кир/латин, допускаем дефисы/цифры
RE_ACRONYM = re.compile(r"\b[А-ЯA-Z]{2,}(?:-[А-ЯA-Z0-9]{2,})*\b")
# КОРОТКИЕ ФРАЗЫ С ЗАГЛАВНЫХ: до 3 слов, чтобы ловить 'Postgres PRO'
RE_CAP_PHRASE = re.compile(
    r"\b(?:[А-ЯA-Z][а-яa-z0-9]{2,})(?:\s+(?:[А-ЯA-Z][а-яa-z0-9]{2,}|PRO|PRO\.|Server|Windows|Postgres))+?\b"
)

def extract_terms_from_paragraph(p: str) -> List[str]:
    terms: set[str] = set()
    for m in RE_ACRONYM.finditer(p):
        terms.add(m.group())
    for m in RE_CAP_PHRASE.finditer(p):
        s = m.group(0)
        # отсечём очень длинные 'фразы'
        if 1 <= s.count(" ") <= 3:
            terms.add(s)
    return sorted(terms)

def scan_files(paths: List[str], cfg: Dict | None = None) -> Dict[str, Dict]:
    """
    Возвращает банк терминов:
    {
      "ЕРВУ": {"count": 42, "examples": ["..."]},
      "Postgres PRO": {"count": 12, "examples": ["..."]}
    }
    """
    # «жёсткий» лоадер без фильтров — чтобы ничего не потерять
    fallback_cfg = {
        "settings": {
            "loader": {
                "filters": {
                    "skip_blank": False, "skip_toc": False, "skip_dotty": False,
                    "skip_pure_number": False, "skip_instr_text": True,
                    "skip_deleted_runs": True
                },
                "normalize": {"strip": True, "collapse_ws": False, "nbsp_to_space": True}
            }
        }
    }
    cfg = cfg or fallback_cfg
    bank: Dict[str, Dict] = {}
    for path in paths:
        try:
            paras = load_paragraphs(path, cfg)
        except Exception:
            continue
        for p in paras:
            for t in extract_terms_from_paragraph(p):
                meta = bank.setdefault(t, {"count": 0, "examples": []})
                meta["count"] += 1
                if len(meta["examples"]) < 5:
                    meta["examples"].append(p[:200])
    return bank

def write_terms_json_csv(bank: Dict[str, Dict], json_path: str, csv_path: str) -> None:
    os.makedirs(os.path.dirname(json_path) or ".", exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"terms": bank}, f, ensure_ascii=False, indent=2)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(["term", "count", "example"])
        for term, meta in sorted(bank.items(), key=lambda kv: (-kv[1]["count"], kv[0])):
            example = meta["examples"][0] if meta["examples"] else ""
            w.writerow([term, meta["count"], example])
