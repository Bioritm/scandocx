# gost_precheck/core/checks/spell.py
from __future__ import annotations
import os
from typing import List, Dict, Tuple
import re

from ..issue import Issue
from ..utils import context_slice
from ..constants import CATEGORY, RID, SEVERITY_ERROR
from ..regexes import RE_RU_WORD, RE_MIXED_CASE

# ---------- словари ----------

def _dict_dir() -> str:
    # dicts лежат рядом с пакетом (в том числе внутри PyInstaller onefile)
    base = os.path.dirname(os.path.dirname(__file__))  # .../core -> ..
    return os.path.join(base, "dicts")

def _read_word_list(path: str) -> List[str]:
    words: List[str] = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                w = line.strip()
                if not w or w.startswith("#"):
                    continue
                words.append(w)
    except Exception:
        pass
    return words

# Грубый, но быстрый русский словарь:
#   - pwl_ru.txt — пользовательские слова (доменные термины)
#   - custom_ru.txt — заготовка с частотными формами/словоформами (можно расширять)
# *Если файлов нет — модуль всё равно работает (использует только эвристику).
def _load_ru_dictionary(cfg: Dict) -> Tuple[set, Dict[Tuple[str, int], List[str]]]:
    ddir = _dict_dir()
    # подключаем пользовательские и кастомные списки
    lst = []
    for name in ("custom_ru.txt", "pwl_ru.txt"):
        lst += _read_word_list(os.path.join(ddir, name))
    base = set()
    for w in lst:
        base.add(w.lower().replace("ё", "е"))

    # индекс для быстрого отбора кандидатов (первая буква + длина ~±2)
    buckets: Dict[Tuple[str, int], List[str]] = {}
    for w in base:
        key = (w[0], len(w))
        buckets.setdefault(key, []).append(w)
        # небольшой дублирующий индекс по длине±1: повышает recall
        buckets.setdefault((w[0], len(w) - 1), []).append(w)
        buckets.setdefault((w[0], len(w) + 1), []).append(w)

    return base, buckets

# ---------- Левенштейн ----------

def _lev(a: str, b: str, max_d: int = 2) -> int:
    # ограниченный Левенштейн (обрываем, когда расстояние > max_d)
    if abs(len(a) - len(b)) > max_d:
        return max_d + 1
    if a == b:
        return 0
    # DP с ранним выходом
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        # эвристический коридор
        lo = max(1, i - max_d)
        hi = min(len(b), i + max_d)
        for j in range(1, len(b) + 1):
            if j < lo or j > hi:
                cur.append(max_d + 1)
                continue
            cost = 0 if ca == b[j - 1] else 1
            cur.append(min(
                prev[j] + 1,       # del
                cur[j - 1] + 1,    # ins
                prev[j - 1] + cost # sub
            ))
        if min(cur) > max_d:
            return max_d + 1
        prev = cur
    return prev[-1]

def _suggest(word: str, ru_index: Dict[Tuple[str, int], List[str]], limit=3) -> List[str]:
    first = word[0]
    L = len(word)
    cands = ru_index.get((first, L), []) + ru_index.get((first, L - 1), []) + ru_index.get((first, L + 1), [])
    scored = []
    # динамический порог: длинные слова допускают 2–3 правки
    max_d = 1 if L <= 5 else (2 if L <= 9 else 3)
    for c in cands:
        d = _lev(word, c, max_d=max_d)
        if d <= max_d:
            scored.append((d, c))
    scored.sort(key=lambda t: (t[0], t[1]))
    return [c for _, c in scored[:limit]]

# ---------- публичная проверка ----------

def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    out: List[Issue] = []
    s_cfg = cfg.get("settings", {}).get("spell", {})
    if not s_cfg.get("enabled", False) or not s_cfg.get("ru", True):
        return out

    min_len = int(s_cfg.get("min_len", 3))
    skip_upper = bool(s_cfg.get("skip_upper", True))
    want_sugg = bool(s_cfg.get("suggestions", True))
    max_sugg = int(s_cfg.get("max_suggestions_per_word", 3))

    # лениво кэшируем словарь на модуль
    global _RU_BASE, _RU_INDEX
    if "_RU_BASE" not in globals():
        _RU_BASE, _RU_INDEX = _load_ru_dictionary(cfg)

    for m in RE_RU_WORD.finditer(paragraph):
        word = m.group(0)
        start = m.start()
        w_norm = word.lower().replace("ё", "е")

        if len(w_norm) < min_len:
            continue
        if skip_upper and word.isupper():
            continue

        # 1) подозрительный смешанный регистр (например: ПРОверку, содерЖит)
        if not (word.islower() or word.istitle() or word.isupper()):
            out.append(Issue(
                idx, start, len(word), SEVERITY_ERROR,
                CATEGORY["SPELL"], RID["SPELL_RU"],
                "Подозрительное смешение регистра в слове",
                context_slice(paragraph, start),
                []
            ))

        # 2) собственно орфография: если слова нет в базовой выборке — ищем поправки
        if w_norm not in _RU_BASE:
            sugg = _suggest(w_norm, _RU_INDEX, limit=max_sugg) if want_sugg else []
            out.append(Issue(
                idx, start, len(word), SEVERITY_ERROR,
                CATEGORY["SPELL"], RID["SPELL_RU"],
                "Возможная орфографическая ошибка (RU)",
                context_slice(paragraph, start),
                sugg
            ))

    return out
