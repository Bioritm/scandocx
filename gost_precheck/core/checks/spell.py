# gost_precheck/core/checks/spell.py
from __future__ import annotations
import os
from typing import List, Dict, Tuple, Set
import re

from ..issue import Issue
from ..utils import context_slice
from ..constants import CATEGORY, RID, SEVERITY_ERROR
from ..regexes import RE_RU_WORD

# ──────────────────────────────────────────────────────────────────────────────
# Пара «быстрых» эвристик, срабатывающих даже без словаря
_RE_MIXED_CASE = re.compile(r"(?u)(?=.*[А-ЯЁ])(?=.*[а-яё]).*|(?=.*[A-Z])(?=.*[a-z]).*")
_RE_TRIPLE_CHAR = re.compile(r"(.)\1\1")   # «инструкциии»
# В русском иногда легальны двойные согласные: сс, нн, лл, тт, мм, рр, кк, пп, жж, зз, чч и т.п.
_ALLOWED_DOUBLE = {"сс","нн","лл","тт","мм","рр","кк","пп","жж","зз","чч","фф","бб","вв","гг","дд"}

# ──────────────────────────────────────────────────────────────────────────────
# Загрузка словаря
def _pkg_dict_dir() -> str:
    # .../core -> .. -> dicts
    base = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(base, "dicts")

def _read_list(path: str) -> List[str]:
    out: List[str] = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                w = line.strip()
                if not w or w.startswith("#"):
                    continue
                out.append(w)
    except Exception:
        pass
    return out

def _load_hunspell_roots(ddir: str) -> Set[str]:
    """Читает ru_RU.dic (если есть) и возвращает набор базовых слов (без флагов)."""
    roots: Set[str] = set()
    dic = os.path.join(ddir, "ru_RU.dic")
    try:
        with open(dic, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                w = line.strip()
                if not w or w.startswith("#"):
                    continue
                # формат: слово[/ФЛАГИ] — берём до слеша
                w = w.split("/")[0]
                if re.fullmatch(r"[А-Яа-яЁё\-]+", w):
                    roots.add(w.lower().replace("ё","е"))
    except Exception:
        pass
    return roots

# частые безопасные суффиксы (очень ограниченно и быстро)
_SUFFIXES = [
    "", "а","у","ой","ою","е","ы","и","ий","ие","ием","ия","ию","ями","ях",
    "ов","ев","ам","ами","ах","ом","ем","ого","ему","ым","ыми",
    "ая","яя","ое","ее","ые","ого","ему","ому","ых","им","их",
]

def _expand_forms(roots: Set[str]) -> Set[str]:
    """Грубое расширение: добавляем часть словоформ (покрытие растёт, шум не растёт)."""
    out: Set[str] = set()
    for r in roots:
        out.add(r)
        base = r
        # простые варианты: «проект», «проектн», «проектир»
        # генерация окончаний только если слово не слишком короткое
        for s in _SUFFIXES:
            if len(base) >= 3:
                out.add((base + s).lower())
    return out

def _build_index(base: Set[str]) -> Dict[Tuple[str,int], List[str]]:
    buckets: Dict[Tuple[str,int], List[str]] = {}
    for w in base:
        if not w:
            continue
        key = (w[0], len(w))
        buckets.setdefault(key, []).append(w)
        # память немного, а recall заметно выше:
        buckets.setdefault((w[0], len(w)-1), []).append(w)
        buckets.setdefault((w[0], len(w)+1), []).append(w)
    return buckets

def _load_ru_dictionary(cfg: Dict) -> Tuple[Set[str], Dict[Tuple[str,int], List[str]]]:
    ddir = _pkg_dict_dir()

    # 1) пользовательские списки
    base: Set[str] = set()
    for name in ("custom_ru.txt", "pwl_ru.txt"):
        for w in _read_list(os.path.join(ddir, name)):
            base.add(w.lower().replace("ё","е"))

    # 2) hunspell roots (+ грубое расширение форм), если есть ru_RU.dic
    roots = _load_hunspell_roots(ddir)
    if roots:
        base |= _expand_forms(roots)

    # 3) опциональный путь из конфига (если указали свой список)
    pwl_cfg = (cfg.get("settings", {})
                 .get("spell", {})
                 .get("pwl_path", "")) or ""
    if pwl_cfg:
        for w in _read_list(pwl_cfg):
            base.add(w.lower().replace("ё","е"))

    return base, _build_index(base)

# ──────────────────────────────────────────────────────────────────────────────
# ограниченный Левенштейн
def _lev(a: str, b: str, max_d: int = 2) -> int:
    if abs(len(a) - len(b)) > max_d:
        return max_d + 1
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        lo = max(1, i - max_d)
        hi = min(len(b), i + max_d)
        for j in range(1, len(b) + 1):
            if j < lo or j > hi:
                cur.append(max_d + 1)
                continue
            cost = 0 if ca == b[j-1] else 1
            cur.append(min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + cost))
        if min(cur) > max_d:
            return max_d + 1
        prev = cur
    return prev[-1]

def _suggest(word: str, index: Dict[Tuple[str,int], List[str]], limit=3) -> List[str]:
    word = word.lower()
    first = word[0]
    L = len(word)
    cands = index.get((first, L), []) + index.get((first, L-1), []) + index.get((first, L+1), [])
    max_d = 1 if L <= 5 else (2 if L <= 9 else 3)
    scored = []
    for c in cands:
        d = _lev(word, c, max_d=max_d)
        if d <= max_d:
            scored.append((d, c))
    scored.sort(key=lambda t: (t[0], t[1]))
    return [c for _, c in scored[:limit]]

def _looks_like_multi_typo(w: str) -> bool:
    wl = w.lower()
    if _RE_TRIPLE_CHAR.search(wl):
        return True
    # «поддробные»: двойная, которая редко легальна в середине
    for i in range(len(wl)-1):
        if wl[i] == wl[i+1]:
            pair = wl[i:i+2]
            if pair not in _ALLOWED_DOUBLE:
                return True
    return False

# ──────────────────────────────────────────────────────────────────────────────

def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    out: List[Issue] = []
    s_cfg = cfg.get("settings", {}).get("spell", {}) or {}
    if not s_cfg.get("enabled", False) or not s_cfg.get("ru", True):
        return out

    min_len   = int(s_cfg.get("min_len", 3))
    skip_upper= bool(s_cfg.get("skip_upper", True))
    want_sugg = bool(s_cfg.get("suggestions", True))
    max_sugg  = int(s_cfg.get("max_suggestions_per_word", 3))
    emit_only_with_suggestions = bool(s_cfg.get("emit_only_with_suggestions", True))

    # Кэш словаря на уровень модуля
    global _RU_BASE, _RU_INDEX
    if "_RU_BASE" not in globals():
        _RU_BASE, _RU_INDEX = _load_ru_dictionary(cfg)

    for m in RE_RU_WORD.finditer(paragraph):
        word  = m.group(0)
        start = m.start()
        w_norm = word.lower().replace("ё","е")

        if len(w_norm) < min_len:
            continue
        if skip_upper and word.isupper():
            continue
        # игнорируем смешанные с латиницей/цифрами токены (CSV, GUID, ORM и т.п.)
        if re.search(r"[A-Za-z0-9]", word):
            continue

        # сигналы явной «неаккуратности» — репортим без словаря
        if _RE_MIXED_CASE.fullmatch(word) or _looks_like_multi_typo(word):
            out.append(Issue(
                idx, start, len(word), SEVERITY_ERROR,
                CATEGORY["SPELL"], RID.get("SPELL_MULTI", "SPELL_MULTI"),
                "Подозрительная орфография",
                context_slice(paragraph, start),
                []
            ))
            continue

        # уже «в словаре»
        if w_norm in _RU_BASE:
            continue

        sugg = _suggest(w_norm, _RU_INDEX, limit=max_sugg) if want_sugg and _RU_INDEX else []
        if emit_only_with_suggestions and not sugg:
            # Нет в базе и нет кандидатов — считаем нормальным словом (не шумим)
            continue

        out.append(Issue(
            idx, start, len(word), SEVERITY_ERROR,
            CATEGORY["SPELL"], RID.get("SPELL_RU", "SPELL_RU"),
            "Возможная орфографическая ошибка (RU)",
            context_slice(paragraph, start),
            sugg
        ))

    return out
