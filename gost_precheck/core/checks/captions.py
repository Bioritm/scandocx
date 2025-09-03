# gost_precheck/core/checks/captions.py
from __future__ import annotations
from typing import List, Dict, Tuple
import re
from ..issue import Issue
from ..constants import CATEGORY, RID, SEVERITY_ERROR, SEVERITY_WARN
from ..utils import context_slice

# "Таблица 1 — Заголовок", "Рисунок 2 — Название", "Рис. 3 — Название"
RE_CAPTION = re.compile(
    r"^(?P<kind>Таблица|Рисунок|Рис\.)\s+(?P<num>\d+(?:\.\d+)*)\s*(?P<dash>[—\-])\s*(?P<title>.*)$",
    re.IGNORECASE
)

def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    issues: List[Issue] = []
    m = RE_CAPTION.match(paragraph)
    if not m:
        return issues

    dash = m.group("dash")
    title = (m.group("title") or "").strip()

    if dash != "—":
        issues.append(Issue(
            idx, m.start("dash"), len(dash),
            SEVERITY_ERROR, CATEGORY["Знаки препинания"], RID["PUNCT_DASH_IN_CAPTION"],
            "В подписях после номера должно быть длинное тире «—», а не дефис '-'",
            context_slice(paragraph, m.start("dash")),
            [" — "]
        ))
        issues.append(Issue(
            idx, m.start("dash"), len(dash),
            SEVERITY_ERROR, CATEGORY["Подписи таблиц/рисунков"], RID["CAPTION_BAD_DASH"],
            "В подписи должно быть длинное тире «—»",
            context_slice(paragraph, m.start("dash")),
            ["—"]
        ))

    if not title:
        issues.append(Issue(
            idx, m.end("dash"), 1,
            SEVERITY_ERROR, CATEGORY["Подписи таблиц/рисунков"], RID["CAPTION_EMPTY_TITLE"],
            "Отсутствует название после тире",
            context_slice(paragraph, m.end("dash")),
            []
        ))
    return issues

def collect_numbers(paragraph: str, idx: int) -> List[Tuple[str, str, int]]:
    m = RE_CAPTION.match(paragraph)
    if not m:
        return []
    kind = m.group("kind")
    num = m.group("num")
    return [(kind, num, idx)]

def numbering_issues(all_nums: List[Tuple[str,str,int]], scope: str="global") -> List[Issue]:
    issues: List[Issue] = []
    seen = set()
    for kind, num, idx in all_nums:
        key = (kind.lower(), num)
        if key in seen:
            issues.append(Issue(
                idx, 0, 0,
                SEVERITY_WARN, CATEGORY["Подписи таблиц/рисунков"], RID["CAPTION_DUP_NUMBER"],
                f"Дублируется номер подписи: {kind} {num}",
                "...", []
            ))
        else:
            seen.add(key)
    return issues
