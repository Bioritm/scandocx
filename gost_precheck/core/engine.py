# gost_precheck/core/engine.py
from typing import List, Dict, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

from .issue import Issue
from .loader import load_paragraphs

# Явные импорты правил — PyInstaller-дружественно
from .checks import whitespace, punctuation, abbr, brands, gost34, captions, ws_word_digit
try:
    from .checks import spell as spell_mod
except Exception:
    spell_mod = None

# Бустер «множественных очепяток» (эвристика Damerau-Levenshtein)
try:
    from .checks import spell_multi as spell_multi_mod
except Exception:
    spell_multi_mod = None

# Порядок важен лишь для стабильной сортировки вывода
REGEX_MODULES = [whitespace, punctuation, abbr, brands, gost34, ws_word_digit, captions]


def _regex_task(i: int, p: str, cfg: Dict):
    out: List[Issue] = []
    nums: List[Any] = []
    errs: List[str] = []

    # 1) обычные быстрые правила
    for mod in REGEX_MODULES:
        try:
            out.extend(mod.check(p, i, cfg))
        except Exception as e:
            errs.append(f"{mod.__name__}.check: {e}")

    # 2) сбор номеров подписей для глобальной проверки последовательности
    try:
        nums = captions.collect_numbers(p, i)
    except Exception as e:
        errs.append(f"captions.collect_numbers: {e}")

    # 3) бустер орфографии (работает в потоках, если включён в settings.spell_booster.enabled)
    try:
        sb = cfg.get("settings", {}).get("spell_booster", {}) or {}
        if spell_multi_mod and sb.get("enabled", False):
            out.extend(spell_multi_mod.check(p, i, cfg))
    except Exception as e:
        errs.append(f"spell_multi.check: {e}")

    return i, out, nums, errs


def _spell_task(i: int, p: str, cfg: Dict):
    errs: List[str] = []
    out: List[Issue] = []
    try:
        if spell_mod and cfg.get("settings", {}).get("spell", {}).get("enabled", False):
            out = spell_mod.check(p, i, cfg)
    except Exception as e:
        errs.append(f"spell.check: {e}")
    return i, out, errs


def analyze_file(path: str, cfg: Dict) -> Tuple[List[Issue], Dict[str, int], Dict[str, Any]]:
    loaded = load_paragraphs(path, cfg)
    if isinstance(loaded, tuple) and len(loaded) == 2:
        paragraphs, loader_stats = loaded
    else:
        paragraphs, loader_stats = loaded, {}

    issues: List[Issue] = []
    all_numbers: List[Any] = []
    internal_errors: List[str] = []

    # Этап 1: потоковые (regex + spell_booster)
    threads = int(cfg.get("settings", {}).get("regex_workers", 0)) or None
    if paragraphs:
        with ThreadPoolExecutor(max_workers=threads) as ex:
            futs = [ex.submit(_regex_task, i, paragraphs[i], cfg) for i in range(len(paragraphs))]
            for f in as_completed(futs):
                idx, iss, nums, errs = f.result()
                issues.extend(iss)
                all_numbers.extend(nums)
                internal_errors.extend(errs)

    # Этап 2: нумерация подписей (глобальная последовательность/дубли)
    try:
        scope = cfg.get("settings", {}).get("numbering_scope", "global")
        issues.extend(captions.numbering_issues(all_numbers, scope=scope))
    except Exception as e:
        internal_errors.append(f"captions.numbering_issues: {e}")

    # Этап 3: классическая орфография (в отдельных процессах)
    spell_cfg = cfg.get("settings", {}).get("spell", {}) or {}
    if spell_mod and spell_cfg.get("enabled", False) and paragraphs:
        workers = int(spell_cfg.get("parallel_workers", 0)) or None
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_spell_task, i, paragraphs[i], cfg) for i in range(len(paragraphs))]
            for f in as_completed(futs):
                idx, iss, errs = f.result()
                issues.extend(iss)
                internal_errors.extend(errs)

    # Агрегация
    by_category: Dict[str, int] = {}
    for it in issues:
        by_category[it.category] = by_category.get(it.category, 0) + 1

    severity_rank = {"ошибка": 0, "предупреждение": 1}
    issues.sort(key=lambda x: (severity_rank.get(x.severity, 9), x.para_index, x.offset, x.rule_id))

    debug_meta = {"loader_stats": loader_stats, "internal_errors": internal_errors}
    return issues, by_category, debug_meta
