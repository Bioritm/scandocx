# gost_precheck/core/checks/whitespace.py
from typing import List, Dict
from ..issue import Issue
from ..constants import CATEGORY, RID, SEVERITY_ERROR, SEVERITY_WARN
from ..utils import context_slice
from ..regexes import (
    RE_DOUBLE_SPACES, RE_TABS, RE_LEADING_TABS, RE_TRAILING,
    RE_PAREN_SPACE_AFTER_OPEN, RE_PAREN_SPACE_BEFORE_CLOSE,
)

def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    issues: List[Issue] = []
    if not paragraph:
        return issues

    # двойные пробелы
    for m in RE_DOUBLE_SPACES.finditer(paragraph):
        issues.append(Issue(
            idx, m.start(), len(m.group()),
            SEVERITY_ERROR, CATEGORY['WS'], RID['WS_DOUBLE_SPACES'],
            "Обнаружены двойные пробелы.",
            context_slice(paragraph, m.start()),
            ["один пробел"]
        ))

    # табы в начале строки
    for m in RE_LEADING_TABS.finditer(paragraph):
        issues.append(Issue(
            idx, m.start(), len(m.group()),
            SEVERITY_ERROR, CATEGORY['WS'], RID['WS_TABS'],
            "Символ табуляции в начале строки — используйте пробелы.",
            context_slice(paragraph, m.start()),
            ["заменить таб на пробелы"]
        ))

    # табы где угодно
    for m in RE_TABS.finditer(paragraph):
        issues.append(Issue(
            idx, m.start(), len(m.group()),
            SEVERITY_ERROR, CATEGORY['WS'], RID['WS_TABS'],
            "Символ табуляции в тексте — используйте пробелы.",
            context_slice(paragraph, m.start()),
            ["заменить таб на пробелы"]
        ))

    # пробел сразу после '('
    for m in RE_PAREN_SPACE_AFTER_OPEN.finditer(paragraph):
        issues.append(Issue(
            idx, m.start(), 2,
            SEVERITY_ERROR, CATEGORY['WS'], RID['PAREN_SPACE_AFTER_OPEN'],
            "Пробел сразу после «(» недопустим.",
            context_slice(paragraph, m.start()),
            ["("]
        ))

    # пробел перед ')'
    for m in RE_PAREN_SPACE_BEFORE_CLOSE.finditer(paragraph):
        issues.append(Issue(
            idx, m.start(), 2,
            SEVERITY_ERROR, CATEGORY['WS'], RID['PAREN_SPACE_BEFORE_CLOSE'],
            "Пробел перед «)» недопустим.",
            context_slice(paragraph, m.start()),
            [")"]
        ))

    # хвостовые пробелы — по флагу
    warn_ws_trailing = bool(cfg.get("settings", {}).get("warnings", {}).get("WS_TRAILING", True))
    if warn_ws_trailing:
        m = RE_TRAILING.search(paragraph)
        if m:
            issues.append(Issue(
                idx, m.start(), len(m.group()),
                SEVERITY_WARN, CATEGORY['WS'], RID['WS_TRAILING'],
                "Лишний пробел(ы) в конце строки.",
                context_slice(paragraph, m.start()),
                []
            ))

    return issues
