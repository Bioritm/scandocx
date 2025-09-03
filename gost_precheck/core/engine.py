# gost_precheck/core/engine.py
from typing import List, Dict, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

from .issue import Issue
from .loader import load_paragraphs

# Явные импорты правил (PyInstaller-friendly)
from .checks import whitespace, punctuation, abbr, brands, gost34, captions, ws_word_digit
try:
    from .checks import spell as spell_mod
except Exception:
    spell_mod = None

REGEX_MODULES = [whitespace, punctuation, abbr, brands, gost34, ws_word_digit, captions]

def _regex_task(i: int, p: str, cfg: Dict):
    issues: List[Issue] = []
    nums: List[Any] = []
    errs: List[str] = []
    for mod in REGEX_MODULES:
        try:
            issues.extend(mod.check(p, i, cfg))
        except Exception as e:
            errs.append(f"{mod.__name__}.check: {e}")
    try:
        nums = captions.collect_numbers(p, i)
    except Exception as e:
        errs.append(f"captions.collect_numbers: {e}")
    return i, issues, nums, errs

def _spell_task(i: int, p: str, cfg: Dict):
    errs: List[str] = []
    out: List[Issue] = []
    try:
        if spell_mod and cfg.get("settings", {}).get("spell", {}).get("enabled", False):
            out = spell_mod.check(p, i, cfg)
    except Exception as e:
        errs.append(f"spell.check: {e}")
    return i, out, errs

def analyze_file(path: str, cfg: Dict) -> Tuple[List[Issue], Dict[str,int], Dict[str,Any]]:
    paragraphs, loader_stats = load_paragraphs(path, cfg)
    issues: List[Issue] = []
    numbers: List[Any] = []
    internal_errors: List[str] = []

    # 1) быстрые проверки
    max_threads = int(cfg.get("settings", {}).get("regex_workers", 0)) or None
    with ThreadPoolExecutor(max_workers=max_threads) as ex:
        for f in as_completed([ex.submit(_regex_task, i, paragraphs[i], cfg) for i in range(len(paragraphs))]):
            idx, iss, nums, errs = f.result()
            issues.extend(iss)
            numbers.extend(nums)
            internal_errors.extend(errs)

    # 2) нумерация подписей
    try:
        scope = cfg.get("settings", {}).get("numbering_scope", "global")
        issues.extend(captions.numbering_issues(numbers, scope=scope))
    except Exception as e:
        internal_errors.append(f"captions.numbering_issues: {e}")

    # 3) орфография
    spell_cfg = cfg.get("settings", {}).get("spell", {})
    if spell_mod and spell_cfg.get("enabled", False):
        workers = int(spell_cfg.get("parallel_workers", 0)) or None
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for f in as_completed([ex.submit(_spell_task, i, paragraphs[i], cfg) for i in range(len(paragraphs))]):
                idx, iss, errs = f.result()
                issues.extend(iss)
                internal_errors.extend(errs)

    by_category: Dict[str,int] = {}
    for it in issues:
        by_category[it.category] = by_category.get(it.category, 0) + 1

    sev = {"ошибка":0, "предупреждение":1}
    issues.sort(key=lambda x: (sev.get(x.severity, 9), x.para_index, x.offset, x.rule_id))

    debug_meta = {"loader_stats": loader_stats, "internal_errors": internal_errors}
    return issues, by_category, debug_meta
