# gost_precheck/core/checks/ws_word_digit.py
from typing import List, Dict
from ..issue import Issue
from ..constants import CATEGORY, RID, SEVERITY_ERROR
from ..regexes import RE_WORD_DIGIT
from ..utils import context_slice

def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    issues: List[Issue] = []
    for m in RE_WORD_DIGIT.finditer(paragraph):
        issues.append(Issue(
            idx, m.start(), len(m.group()), SEVERITY_ERROR,
            CATEGORY['WS'], RID['WS_WORD_DIGIT'],
            "Слитное написание «слово+цифра» — вставьте пробел",
            context_slice(paragraph, m.start()),
            # подсказка: «Процедура 1»
            [m.group().rstrip("0123456789") + " " + "".join([c for c in m.group() if c.isdigit()])]
        ))
    return issues
