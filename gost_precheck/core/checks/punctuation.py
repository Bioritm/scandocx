# gost_precheck/core/checks/punctuation.py
from typing import List, Dict

from ..issue import Issue
from ..constants import CATEGORY, RID, SEVERITY_ERROR
from ..utils import context_slice
from ..regexes import (
    RE_SPACE_BEFORE_PUNCT,
    RE_NO_SPACE_AFTER_PUNCT,
    RE_DOUBLE_COMMA,
    RE_DOUBLE_SEMI,
    RE_DOUBLE_COLON,
    RE_TWO_DOTS,
    RE_MANY_DOTS,
    RE_PAREN_SPACE_AFTER_OPEN,
    RE_PAREN_SPACE_BEFORE_CLOSE,
    RE_CYR_LAT_NO_SPACE,
)

# необязательные «умные» паттерны (есть не во всех сборках)
try:
    from ..regexes import RE_HYPHEN_AS_DASH_SMART as RE_HYPHEN_AS_DASH_X
except Exception:
    from ..regexes import RE_HYPHEN_AS_DASH as RE_HYPHEN_AS_DASH_X

try:
    from ..regexes import RE_STRAIGHT_QUOTES_SMART as RE_STRAIGHT_QUOTES_X
except Exception:
    from ..regexes import RE_STRAIGHT_QUOTES as RE_STRAIGHT_QUOTES_X  # type: ignore

try:
    from ..regexes import RE_EMDASH_TIGHT
except Exception:
    RE_EMDASH_TIGHT = None  # опционально

SEVERITY_WARNING = "предупреждение"


def _has_any(s: str, chars: str) -> bool:
    return any(c in s for c in chars)


def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    issues: List[Issue] = []
    if not paragraph or len(paragraph) < 2:
        return issues

    # Грубые флаги: не подсвечиваем кавычки/скобки в коде/URL
    looks_like_code = "://" in paragraph or "`" in paragraph

    # 1) Лишний пробел ПЕРЕД знаком препинания
    if _has_any(paragraph, " ,.;:!?"):
        for m in RE_SPACE_BEFORE_PUNCT.finditer(paragraph):
            issues.append(Issue(
                idx, m.start(), 1,
                SEVERITY_ERROR, CATEGORY['PUNCT'], RID['PUNCT_SPACE_BEFORE'],
                "Лишний пробел перед знаком препинания",
                context_slice(paragraph, m.start()),
                ["убрать пробел"]
            ))

    # 2) Нет пробела ПОСЛЕ знака препинания
    if _has_any(paragraph, ",;:!?"):
        for m in RE_NO_SPACE_AFTER_PUNCT.finditer(paragraph):
            pos = m.start(1)
            issues.append(Issue(
                idx, pos, 1,
                SEVERITY_ERROR, CATEGORY['PUNCT'], RID['PUNCT_NO_SPACE_AFTER'],
                "Нет пробела после знака препинания",
                context_slice(paragraph, pos),
                ["добавить пробел после знака"]
            ))

    # 3) Дубли знаков
    if _has_any(paragraph, ",;:"):
        for m in RE_DOUBLE_COMMA.finditer(paragraph):
            issues.append(Issue(
                idx, m.start(), 2,
                SEVERITY_ERROR, CATEGORY['PUNCT'], RID['PUNCT_DOUBLE_COMMA'],
                "Две запятые подряд",
                context_slice(paragraph, m.start()),
                [","]
            ))
        for m in RE_DOUBLE_SEMI.finditer(paragraph):
            issues.append(Issue(
                idx, m.start(), 2,
                SEVERITY_ERROR, CATEGORY['PUNCT'], RID['PUNCT_DOUBLE_SEMI'],
                "Две точки с запятой подряд",
                context_slice(paragraph, m.start()),
                [";"]
            ))
        for m in RE_DOUBLE_COLON.finditer(paragraph):
            issues.append(Issue(
                idx, m.start(), 2,
                SEVERITY_ERROR, CATEGORY['PUNCT'], RID['PUNCT_DOUBLE_COLON'],
                "Два двоеточия подряд",
                context_slice(paragraph, m.start()),
                [":"]
            ))

    # 4) Точки / многоточие — порядок важен: сначала 4+, потом ровно две
    # Чтобы не репортить одно и то же место дважды.
    used_spans = []

    def _overlaps(a, b):
        return not (a[1] <= b[0] or b[1] <= a[0])

    if "." in paragraph:
        for m in RE_MANY_DOTS.finditer(paragraph):
            span = m.span()
            used_spans.append(span)
            issues.append(Issue(
                idx, span[0], span[1] - span[0],
                SEVERITY_ERROR, CATEGORY['PUNCT'], RID['PUNCT_MANY_DOTS'],
                "Четыре и более точек — используйте «…»",
                context_slice(paragraph, span[0]),
                ["…"]
            ))
        for m in RE_TWO_DOTS.finditer(paragraph):
            span = m.span()
            if any(_overlaps(span, u) for u in used_spans):
                continue
            issues.append(Issue(
                idx, span[0], 2,
                SEVERITY_ERROR, CATEGORY['PUNCT'], RID['PUNCT_TWO_DOTS'],
                "Ровно две точки — используйте «…»",
                context_slice(paragraph, span[0]),
                ["…"]
            ))

    # 5) Дефис между словами вместо длинного тире «—»
    if " - " in paragraph:
        for m in RE_HYPHEN_AS_DASH_X.finditer(paragraph):
            issues.append(Issue(
                idx, m.start(), 3,
                SEVERITY_ERROR, CATEGORY['PUNCT'],
                RID.get('PUNCT_HYPHEN_AS_DASH', 'PUNCT_HYPHEN_AS_DASH'),
                "Между словами должно быть длинное тире «—» с пробелами, а не дефис '-'",
                context_slice(paragraph, m.start()),
                [" — "]
            ))

    # 6) Эм-тире без пробелов вокруг: слово—слово
    if RE_EMDASH_TIGHT and "—" in paragraph:
        for m in RE_EMDASH_TIGHT.finditer(paragraph):
            issues.append(Issue(
                idx, m.start(), 1,
                SEVERITY_ERROR, CATEGORY['PUNCT'],
                RID.get('DASH_SPACING', 'DASH_SPACING'),
                "Вокруг «—» нужны пробелы: «слово — слово»",
                context_slice(paragraph, m.start()),
                [" — "]
            ))

    # 7) Прямые кавычки "..." (не трогаем дюймы и код/URL)
    if not looks_like_code and '"' in paragraph:
        for m in RE_STRAIGHT_QUOTES_X.finditer(paragraph):
            issues.append(Issue(
                idx, m.start(), len(m.group()),
                SEVERITY_WARNING, CATEGORY['PUNCT'],
                RID.get('PUNCT_STRAIGHT_QUOTES', 'PUNCT_STRAIGHT_QUOTES'),
                "Прямые кавычки — используйте «ёлочки»",
                context_slice(paragraph, m.start()),
                ["«…»"]
            ))

    # 8) Лишние пробелы в скобках — пропускаем код/URL
    if not looks_like_code and _has_any(paragraph, "()"):
        for m in RE_PAREN_SPACE_AFTER_OPEN.finditer(paragraph):
            issues.append(Issue(
                idx, m.start(), 2,
                SEVERITY_ERROR, CATEGORY['PUNCT'],
                RID.get('PUNCT_PAREN_SPACE_OPEN', 'PUNCT_PAREN_SPACE_OPEN'),
                "Пробел сразу после открывающей скобки недопустим",
                context_slice(paragraph, m.start()),
                ["("]
            ))
        for m in RE_PAREN_SPACE_BEFORE_CLOSE.finditer(paragraph):
            issues.append(Issue(
                idx, m.start(), 2,
                SEVERITY_ERROR, CATEGORY['PUNCT'],
                RID.get('PUNCT_PAREN_SPACE_CLOSE', 'PUNCT_PAREN_SPACE_CLOSE'),
                "Пробел перед закрывающей скобкой недопустим",
                context_slice(paragraph, m.start()),
                [")"]
            ))

    # 9) Стык кириллица↔латиница без пробела (ослабленная эвристика)
    #    Не ругаемся, если рядом явная пунктуация.
    if _has_any(paragraph, 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя'):
        for m in RE_CYR_LAT_NO_SPACE.finditer(paragraph):
            pos = m.start()
            left = paragraph[pos - 1] if pos > 0 else ""
            right = paragraph[pos] if pos < len(paragraph) else ""
            if left in ",;:()" or right in ",;:()":
                continue
            issues.append(Issue(
                idx, pos, 1,
                SEVERITY_ERROR, CATEGORY['PUNCT'],
                RID.get('PUNCT_CYR_LAT_JOIN', 'PUNCT_CYR_LAT_JOIN'),
                "Нет пробела между кириллицей и латиницей",
                context_slice(paragraph, pos),
                ["вставить пробел"]
            ))

    return issues
