# gost_precheck/core/checks/ws_word_digit.py
import re
from typing import List, Dict

from ..issue import Issue
from ..constants import CATEGORY, RID, SEVERITY_ERROR
from ..utils import context_slice

try:
    # не импортируем символ напрямую, чтобы не падать в frozen-окружении
    from .. import regexes as rx
except Exception:
    rx = None

# Резервный паттерн на случай отсутствия RE_WORD_DIGIT в regexes
_FALLBACK_RE_WORD_DIGIT = re.compile(
    r"(?<![\d\W])[A-Za-zА-Яа-яЁё]+(?:-[A-Za-zА-Яа-яЁё]+)?\d+"
)

def _is_allowed(token: str, cfg: Dict) -> bool:
    """
    Исключения: можно расширять через конфиг, если нужно.
    Например, не ругаться на ГОСТ201, ОКПД2 и т.п.
    """
    allow = set(map(str.lower, cfg.get("settings", {}).get("word_digit_allow", [])))
    return token.lower() in allow

def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    if not paragraph:
        return []
    pat = getattr(rx, "RE_WORD_DIGIT", _FALLBACK_RE_WORD_DIGIT) if rx else _FALLBACK_RE_WORD_DIGIT

    issues: List[Issue] = []
    for m in pat.finditer(paragraph):
        token = m.group(0)
        if _is_allowed(token, cfg):
            continue
        issues.append(Issue(
            idx, m.start(), len(token),
            SEVERITY_ERROR, CATEGORY['WS'], RID.get('WS_WORD_DIGIT', 'WS_WORD_DIGIT'),
            "Слитно слово+цифра — нужен пробел (например: «Процедура 1»). Если это допустимо, добавьте в word_digit_allow.",
            context_slice(paragraph, m.start()),
            ["вставить пробел"]
        ))
    return issues
