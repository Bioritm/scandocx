# gost_precheck/core/checks/spell_multi.py
# Простая офлайн-эвристика "множественных очепяток" (Damerau-Levenshtein + повторы)
# без pyenchant/hunspell. Работает по словарю ru_RU.dic (+ PWL + частотный список).

from __future__ import annotations
import os, io, re
from typing import Dict, List, Set, Tuple, DefaultDict
from collections import defaultdict

from ..issue import Issue
from ..constants import CATEGORY, RID, SEVERITY_ERROR
from ..utils import context_slice

_WORD = re.compile(r"[A-Za-zА-Яа-яЁё\-]{3,}")
_REPEAT3 = re.compile(r"(.)\1\1+")  # "инструкциии", "поддробные"
_CYR = re.compile(r"[А-Яа-яЁё]")

# Кэш словарей между вызовами (на процесс)
_VOCAB_CACHE: Dict[str, "Vocab"] = {}

class Vocab:
    def __init__(self, words: Set[str]):
        # нормализуем в нижний регистр
        base = {w.strip().lower() for w in words if w and len(w) >= 2}
        self.words: Set[str] = base
        # индексация по (первая_буква, длина)
        index: DefaultDict[Tuple[str, int], List[str]] = defaultdict(list)
        for w in base:
            key = (w[0], len(w))
            index[key].append(w)
        self.index = index

    def known(self, w: str) -> bool:
        return w.lower() in self.words

    def candidates(self, w: str, max_delta: int = 2) -> List[str]:
        w = w.lower()
        out: List[str] = []
        first = w[0]
        L = len(w)
        for d in range(-max_delta, max_delta + 1):
            key = (first, L + d)
            if key in self.index:
                out.extend(self.index[key])
        return out


def _resolve_dict_dir(cfg: Dict) -> str | None:
    """settings.spell.dict_dir:
       - 'auto' → <папка пакета>/gost_precheck/dicts
       - путь → берём как есть
    """
    spell = cfg.get("settings", {}).get("spell", {}) or {}
    dd = spell.get("dict_dir", "auto")
    if dd and dd != "auto":
        return dd
    # auto
    base = os.path.dirname(os.path.abspath(__file__))  # .../core/checks
    # поднимаемся к пакету gost_precheck
    pkg = os.path.abspath(os.path.join(base, "..", ".."))
    cand = os.path.join(pkg, "dicts")
    return cand if os.path.isdir(cand) else None


def _read_lines(path: str) -> List[str]:
    try:
        with io.open(path, "r", encoding="utf-8", errors="ignore") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception:
        return []


def _load_ru_dic(dict_dir: str | None) -> Set[str]:
    """Берём ru_RU.dic (если есть). Первая строка может быть счётчиком — игнорируем."""
    out: Set[str] = set()
    if not dict_dir:
        return out
    dic = os.path.join(dict_dir, "ru_RU.dic")
    if not os.path.isfile(dic):
        return out
    lines = _read_lines(dic)
    if not lines:
        return out
    # первая строка иногда "N" — размер словаря hunspell
    if lines and lines[0].isdigit():
        lines = lines[1:]
    for ln in lines:
        # формат "слово[/FLAGS]"; берём до '/'
        w = ln.split("/")[0].strip()
        if w:
            out.add(w)
    return out


def _load_freq_words(cfg: Dict, dict_dir: str | None) -> Set[str]:
    """Подмешиваем частотный список (если положишь файл). Ищем:
       - settings.spell.freq_ru_path
       - <pkg>/dicts/freq_ru.txt
    """
    spell = cfg.get("settings", {}).get("spell", {}) or {}
    paths = []
    if spell.get("freq_ru_path"):
        paths.append(spell["freq_ru_path"])
    if dict_dir:
        paths.append(os.path.join(dict_dir, "freq_ru.txt"))

    out: Set[str] = set()
    for p in paths:
        if p and os.path.isfile(p):
            out.update(_read_lines(p))
            break

    # Минимальный fallback, если файлов нет (чуть-чуть частых слов)
    if not out:
        out.update({
            "данные","документ","версия","установка","инструкция","система","пользователь",
            "база","данных","сервер","процесс","структура","создание","пустая","копирование",
            "описание","раздел","компонент","решение","комментарий","плагин","актуальный",
            "документация","поставщик","сайт","шаг","таблица","рисунок"
        })
    return out


def _load_pwl(cfg: Dict, dict_dir: str | None) -> Set[str]:
    """Personal Word List: settings.spell.pwl_path или рядом: pwl_ru.txt / custom_ru.txt"""
    spell = cfg.get("settings", {}).get("spell", {}) or {}
    cands = []
    if spell.get("pwl_path"):
        cands.append(spell["pwl_path"])
    if dict_dir:
        cands.append(os.path.join(dict_dir, "pwl_ru.txt"))
        cands.append(os.path.join(dict_dir, "custom_ru.txt"))

    out: Set[str] = set()
    for p in cands:
        if p and os.path.isfile(p):
            out.update(_read_lines(p))
            break
    return out


def _build_vocab(cfg: Dict) -> Vocab:
    key = repr(sorted(cfg.get("settings", {}).get("spell", {}).items()))
    if key in _VOCAB_CACHE:
        return _VOCAB_CACHE[key]

    dict_dir = _resolve_dict_dir(cfg)
    words: Set[str] = set()
    words.update(_load_ru_dic(dict_dir))
    words.update(_load_freq_words(cfg, dict_dir))
    words.update(_load_pwl(cfg, dict_dir))

    # Подмешаем доменные: бренды/abbr из конфига, если они загружены
    brands = cfg.get("brands", {}) or {}
    brand_terms = set()
    for k, v in brands.items():
        if isinstance(v, list):
            for x in v:
                brand_terms.update(_WORD.findall(str(x)))
        elif isinstance(v, str):
            brand_terms.update(_WORD.findall(v))
    words.update(brand_terms)

    vocab = Vocab(words)
    _VOCAB_CACHE[key] = vocab
    return vocab


def _is_upper(word: str) -> bool:
    return word.isupper()


def _mixed_case(word: str) -> bool:
    # "содерЖит", "ПРОверку" — подсветим как странную капитализацию
    return any(c.isupper() for c in word[1:]) and any(c.islower() for c in word[1:])


def _damerau_levenshtein(a: str, b: str, limit: int) -> int:
    # быстрая реализация с ранним выходом
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if abs(la - lb) > limit:
        return limit + 1
    # одномерные буферы
    prev = list(range(lb + 1))
    curr = [0] * (lb + 1)
    for i in range(1, la + 1):
        curr[0] = i
        ai = a[i - 1]
        # окно ограничений
        start = max(1, i - limit)
        end = min(lb, i + limit)
        if start > 1:
            curr[start - 1] = limit + 1
        for j in range(start, end + 1):
            cost = 0 if ai == b[j - 1] else 1
            curr[j] = min(
                prev[j] + 1,       # удаление
                curr[j - 1] + 1,   # вставка
                prev[j - 1] + cost # замена
            )
            # транспозиция
            if i > 1 and j > 1 and ai == b[j - 2] and a[i - 2] == b[j - 1]:
                curr[j] = min(curr[j], prev[j - 2] + cost)
        prev, curr = curr, prev
        # ранний выход: всё хуже лимита
        if min(prev) > limit:
            return limit + 1
    return prev[lb]


def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    """Быстрый эвристический чекер:
       - подчёркивает слова, которых нет в словаре
       - дополнительно подсвечивает повтор 3+ одинаковых букв подряд
       - пытается дать 1–3 подсказки на основе Damerau-Levenshtein
    """
    issues: List[Issue] = []
    if not paragraph:
        return issues

    sb = cfg.get("settings", {}).get("spell_booster", {}) or {}
    enabled = sb.get("enabled", False)
    if not enabled:
        return issues

    min_len = int(sb.get("min_len", 4))
    skip_upper = bool(sb.get("skip_upper", True))
    max_sug = int(sb.get("max_suggestions", 3))
    # порог: абсолютный и относительный
    max_dist = int(sb.get("max_distance", 2))
    ratio = float(sb.get("ratio", 0.34))

    vocab = _build_vocab(cfg)

    for m in _WORD.finditer(paragraph):
        word = m.group()
        if len(word) < min_len:
            continue
        if skip_upper and _is_upper(word):
            continue

        low = word.lower()

        # кириллица — основная цель
        if not _CYR.search(low):
            continue

        # повтор >=3 одинаковых букв
        if _REPEAT3.search(low):
            issues.append(Issue(
                idx, m.start(), len(word),
                SEVERITY_ERROR, CATEGORY["SPELL"], RID.get("SPELL_MULTI", "SPELL_MULTI"),
                "Подозрительная орфография (повтор символов)",
                context_slice(paragraph, m.start()),
                []
            ))
            # не делаем continue — пусть ниже попробуем найти похожие слова

        # если в словаре — ок
        if vocab.known(low):
            continue

        # генерим кандидатов (по первой букве и близкой длине)
        cands = vocab.candidates(low, max_delta=max_dist)
        if not cands:
            # нет кандидатов — всё равно отметим как возможную ошибку
            issues.append(Issue(
                idx, m.start(), len(word),
                SEVERITY_ERROR, CATEGORY["SPELL"], RID.get("SPELL_MULTI", "SPELL_MULTI"),
                "Подозрительная орфография",
                context_slice(paragraph, m.start()),
                []
            ))
            continue

        # считаем расстояния, режем по порогу
        abs_limit = max_dist
        rel_limit = max(1, int(len(low) * ratio))
        limit = max(abs_limit, rel_limit)

        scored: List[Tuple[int, str]] = []
        best = limit + 1
        for c in cands:
            d = _damerau_levenshtein(low, c, limit)
            if d <= limit:
                scored.append((d, c))
                if d < best:
                    best = d

        if not scored:
            issues.append(Issue(
                idx, m.start(), len(word),
                SEVERITY_ERROR, CATEGORY["SPELL"], RID.get("SPELL_MULTI", "SPELL_MULTI"),
                "Подозрительная орфография",
                context_slice(paragraph, m.start()),
                []
            ))
            continue

        scored.sort(key=lambda x: (x[0], len(x[1])))
        sugg = [s for _, s in scored[:max_sug]]
        issues.append(Issue(
            idx, m.start(), len(word),
            SEVERITY_ERROR, CATEGORY["SPELL"], RID.get("SPELL_MULTI", "SPELL_MULTI"),
            "Подозрительная орфография",
            context_slice(paragraph, m.start()),
            sugg
        ))

    return issues
