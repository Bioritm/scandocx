from typing import List, Dict
from ..issue import Issue
from ..constants import CATEGORY, RID, SEVERITY_ERROR
from ..regexes import RE_WORD_DIGIT, RE_DIGIT_WORD
from ..utils import context_slice

def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    issues: List[Issue] = []

    # Слово+число без пробела: "раздел5"
    for m in RE_WORD_DIGIT.finditer(paragraph):
        pos = m.start(2)  # место перед цифрой
        issues.append(
            Issue(
                idx, pos, 0, SEVERITY_ERROR,
                CATEGORY['WS'], RID['WS_NO_SPACE'],
                "Отсутствует пробел между словом и числом",
                context_slice(paragraph, pos),
                ["вставить пробел"]
            )
        )

    # Число+слово без пробела: "5раздел"
    for m in RE_DIGIT_WORD.finditer(paragraph):
        pos = m.start(2)  # место перед буквой
        issues.append(
            Issue(
                idx, pos, 0, SEVERITY_ERROR,
                CATEGORY['WS'], RID['WS_NO_SPACE'],
                "Отсутствует пробел между числом и словом",
                context_slice(paragraph, pos),
                ["вставить пробел"]
            )
        )

    return issues
