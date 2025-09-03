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
    # может не быть в старых regexes.py — обернём использование в try/except
    # RE_CAPTION_BAD_DASH
)

def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    issues: List[Issue] = []
    if not paragraph:
        return issues

    # 1) Лишний пробел перед знаком препинания
    for m in RE_SPACE_BEFORE_PUNCT.finditer(paragraph):
        issues.append(Issue(
            idx, m.start(), 1,
            SEVERITY_ERROR, CATEGORY['PUNCT'], RID['PUNCT_SPACE_BEFORE'],
            "Лишний пробел перед знаком препинания",
            context_slice(paragraph, m.start()),
            ["убрать пробел"]
        ))

    # 2) Нет пробела после знака препинания
    for m in RE_NO_SPACE_AFTER_PUNCT.finditer(paragraph):
        pos = m.start(1)  # сам знак препинания в группе (1)
        issues.append(Issue(
            idx, pos, 1,
            SEVERITY_ERROR, CATEGORY['PUNCT'], RID['PUNCT_NO_SPACE_AFTER'],
            "Нет пробела после знака препинания",
            context_slice(paragraph, pos),
            ["добавить пробел после знака"]
        ))

    # 3) Дубли знаков
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

    # 4) Точки/многоточие
    for m in RE_TWO_DOTS.finditer(paragraph):
        issues.append(Issue(
            idx, m.start(), 2,
            SEVERITY_ERROR, CATEGORY['PUNCT'], RID['PUNCT_TWO_DOTS'],
            "Ровно две точки — используйте «…»",
            context_slice(paragraph, m.start()),
            ["…"]
        ))
    for m in RE_MANY_DOTS.finditer(paragraph):
        issues.append(Issue(
            idx, m.start(), len(m.group()),
            SEVERITY_ERROR, CATEGORY['PUNCT'], RID['PUNCT_MANY_DOTS'],
            "Четыре и более точек — используйте «…»",
            context_slice(paragraph, m.start()),
            ["…"]
        ))

    # 5) Дефис вместо длинного тире в подписях (Таблица/Рисунок N - Название)
    try:
        from ..regexes import RE_CAPTION_BAD_DASH
        for m in RE_CAPTION_BAD_DASH.finditer(paragraph):
            issues.append(Issue(
                idx, m.start(), 1,
                SEVERITY_ERROR, CATEGORY['PUNCT'],
                RID.get('PUNCT_DASH_IN_CAPTION', 'PUNCT_DASH_IN_CAPTION'),
                "В подписях после номера должно быть длинное тире «—», а не дефис '-'",
                context_slice(paragraph, m.start()),
                [" — "]
            ))
    except Exception:
        # Паттерна может не быть в старой сборке — спокойно пропускаем
        pass

    return issues
