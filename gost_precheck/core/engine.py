from typing import List, Dict, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
import sys
from pathlib import Path

# PyInstaller: делаем пакет видимым внутри _MEIPASS
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    sys.path.insert(0, str(Path(sys._MEIPASS)))

from .issue import Issue
from .loader import load_paragraphs

# ✅ ЯВНЫЕ импорты подмодулей (не трогаем checks/__init__.py)
import gost_precheck.core.checks.whitespace as chk_whitespace
import gost_precheck.core.checks.punctuation as chk_punctuation
import gost_precheck.core.checks.abbr as chk_abbr
import gost_precheck.core.checks.brands as chk_brands
import gost_precheck.core.checks.gost34 as chk_gost34
import gost_precheck.core.checks.captions as chk_captions
import gost_precheck.core.checks.spell as chk_spell
import gost_precheck.core.checks.ws_word_digit as chk_ws_word_digit

MODULES = [
    chk_whitespace,
    chk_punctuation,
    chk_abbr,
    chk_brands,
    chk_gost34,
    chk_captions,
    chk_spell,
    chk_ws_word_digit,
]

LOCAL_CHECKS = [m for m in MODULES if m is not chk_captions]
CAPTIONS = chk_captions

def _run_local_checks(args):
    idx, p, cfg = args
    issues: List[Issue] = []
    for mod in LOCAL_CHECKS:
        try:
            issues.extend(mod.check(p, idx, cfg))
        except Exception:
            pass
    numbers = CAPTIONS.collect_numbers(p, idx)
    return (idx, issues, numbers)

def analyze_file(path: str, cfg: Dict) -> Tuple[List[Issue], Dict[str, int]]:
    paras = load_paragraphs(path)
    tasks = ((i, paras[i], cfg) for i in range(len(paras)))

    issues: List[Issue] = []
    numbers = []
    workers = int(cfg["settings"].get("parallel_workers", 0)) or None

    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_run_local_checks, t) for t in tasks]
        for fut in as_completed(futs):
            idx, iss, nums = fut.result()
            issues.extend(iss)
            numbers.extend(nums)

    issues.extend(CAPTIONS.numbering_issues(numbers, scope=cfg["settings"].get("numbering_scope", "global")))
    by_category: Dict[str, int] = {}
    for it in issues:
        by_category[it.category] = by_category.get(it.category, 0) + 1

    severity_rank = {"ошибка": 0, "предупреждение": 1}
    issues.sort(key=lambda x: (severity_rank.get(x.severity, 9), x.para_index, x.offset, x.rule_id))
    return issues, by_category
