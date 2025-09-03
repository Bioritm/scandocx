# gost_precheck/core/checks/post_normalize.py
import re
from typing import List, Dict
from ..issue import Issue
from ..constants import CATEGORY, RID, SEVERITY_WARN
from ..utils import context_slice

# слово-минус-слово, исключая числа по краям
RE_DASH_WORDS = re.compile(r'(?<!\d)(?<=\S)\s-\s(?=\S)(?!\d)')
# также «слепые» случаи без пробелов: слово-слово
RE_DASH_TIGHT  = re.compile(r'(?<!\d)(?<=\S)-(?!\d)(?=\S)')

# "прямые" кавычки
RE_STRAIGHT_QUOTES = re.compile(r'"([^"\n]{1,200})"')

def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    out: List[Issue] = []
    pn = cfg.get("settings", {}).get("post_normalize", {})
    if not (pn.get("dashes") or pn.get("quotes")):
        return out

    if pn.get("dashes"):
        for m in RE_DASH_WORDS.finditer(paragraph):
            out.append(Issue(
                idx, m.start(), m.end()-m.start(), SEVERITY_WARN,
                CATEGORY['NORM'], RID['POSTNORM_DASH'],
                "Между словами используется минус. Рекомендуется «—» с пробелами.",
                context_slice(paragraph, m.start()),
                [" — "]
            ))
        for m in RE_DASH_TIGHT.finditer(paragraph):
            out.append(Issue(
                idx, m.start(), 1, SEVERITY_WARN,
                CATEGORY['NORM'], RID['POSTNORM_DASH'],
                "Между словами используется минус. Рекомендуется «—».",
                context_slice(paragraph, m.start()),
                ["—"]
            ))

    if pn.get("quotes"):
        for m in RE_STRAIGHT_QUOTES.finditer(paragraph):
            repl = f"«{m.group(1)}»"
            out.append(Issue(
                idx, m.start(), len(m.group(0)), SEVERITY_WARN,
                CATEGORY['NORM'], RID['POSTNORM_QUOTES'],
                "Прямые кавычки. Рекомендуются «ёлочки».",
                context_slice(paragraph, m.start()),
                [repl]
            ))

    return out
