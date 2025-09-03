import re
from ..issue import Issue
from ..constants import CATEGORY, RID, SEVERITY_ERROR
from ..utils import context_slice

RE_ABBR_BAD = re.compile(
    r'\b(?:в\s?т\.\s?ч\.|т\.\s?е\.|и\s?т\.\s?д\.|и\s?т\.\s?п\.)',
    re.IGNORECASE
)

RE_ABBR_GOOD = {
    "в т.ч.": "в т. ч.",
    "т.е.": "т. е.",
    "и т.д.": "и т. д.",
    "и т.п.": "и т. п."
}

def _suggest_fixed(text: str) -> str:
    # Нормализуем пробелы после каждой точки
    return (text
            .replace("в т.ч.", "в т. ч.")
            .replace("В т.ч.", "В т. ч.")
            .replace("т.е.", "т. е.")
            .replace("и т.д.", "и т. д.")
            .replace("и т.п.", "и т. п.")
            )

def check(paragraph: str, idx: int, cfg: dict):
    issues = []
    for m in RE_ABBR_BAD.finditer(paragraph):
        bad = m.group(0)
        issues.append(Issue(
            idx, m.start(), len(bad),
            SEVERITY_ERROR, CATEGORY['PUNCT'], RID['ABBR_SPACING'],
            "Неверные пробелы в аббревиатуре (нужно «в т. ч.» / «т. е.» / «и т. д.» / «и т. п.»)",
            context_slice(paragraph, m.start()),
            [_suggest_fixed(bad)]
        ))
    return issues
