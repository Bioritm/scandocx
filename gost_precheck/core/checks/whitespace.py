from typing import List, Dict
from ..issue import Issue
from ..constants import CATEGORY, RID, SEVERITY_ERROR, SEVERITY_WARN
from ..regexes import (
    RE_DOUBLE_SPACES,
    RE_TABS,
    RE_TRAILING,
    RE_PAREN_SPACE_AFTER_OPEN,
    RE_PAREN_SPACE_BEFORE_CLOSE,
)
from ..utils import context_slice


def _ws_trailing_severity(cfg: Dict) -> str | None:
    """
    Возвращает 'ошибка' | 'предупреждение' | None (если игнорировать).
    Управляется settings.ws_trailing: 'error' | 'warn' | 'ignore'
    """
    mode = (cfg.get("settings", {}).get("ws_trailing", "warn") or "warn").lower()
    if mode == "ignore":
        return None
    return "ошибка" if mode == "error" else "предупреждение"


def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    issues: List[Issue] = []

    # табы — всегда предупреждение
    for m in RE_TABS.finditer(paragraph):
        issues.append(
            Issue(
                idx,
                m.start(),
                1,
                SEVERITY_WARN,
                CATEGORY["WS"],
                RID["WS_TABS"],
                "Использован табулятор",
                context_slice(paragraph, m.start()),
            )
        )

    # хвостовые пробелы — по настройке: error|warn|ignore
    sev = _ws_trailing_severity(cfg)
    if sev is not None:
        m = RE_TRAILING.search(paragraph)
        if m:
            issues.append(
                Issue(
                    idx,
                    m.start(),
                    len(m.group()),
                    sev,
                    CATEGORY["WS"],
                    RID["WS_TRAILING"],
                    "Лишний пробел в конце строки",
                    context_slice(paragraph, m.start()),
                )
            )

    # двойные пробелы — ошибка
    for m in RE_DOUBLE_SPACES.finditer(paragraph):
        issues.append(
            Issue(
                idx,
                m.start(),
                len(m.group()),
                SEVERITY_ERROR,
                CATEGORY["WS"],
                RID["WS_DOUBLE_SPACES"],
                "Обнаружены двойные пробелы",
                context_slice(paragraph, m.start()),
            )
        )

    # пробел сразу после «(»
    for m in RE_PAREN_SPACE_AFTER_OPEN.finditer(paragraph):
        issues.append(
            Issue(
                idx,
                m.start(),
                2,
                SEVERITY_ERROR,
                CATEGORY["WS"],
                RID["PAREN_SPACE_AFTER_OPEN"],
                "Пробел сразу после «(»",
                context_slice(paragraph, m.start()),
                ["("],
            )
        )

    # пробел перед «)»
    for m in RE_PAREN_SPACE_BEFORE_CLOSE.finditer(paragraph):
        issues.append(
            Issue(
                idx,
                m.start(),
                2,
                SEVERITY_ERROR,
                CATEGORY["WS"],
                RID["PAREN_SPACE_BEFORE_CLOSE"],
                "Пробел перед «)»",
                context_slice(paragraph, m.start()),
                [")"],
            )
        )

    return issues
