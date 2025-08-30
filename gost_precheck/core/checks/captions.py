
from typing import List, Dict
from ..issue import Issue
from ..constants import CATEGORY, RID, SEVERITY_ERROR, SEVERITY_WARN
from ..utils import context_slice
import re

CAPTION_TABLE_RE = re.compile(r'^\s*Таблица\s+(\d+)\s*([—\-\.])\s*(.+)?', re.IGNORECASE)
CAPTION_FIG_RE = re.compile(r'^\s*(Рисунок|Рис\.)\s+(\d+)\s*([—\-\.])\s*(.+)?', re.IGNORECASE)

def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    issues: List[Issue] = []
    mt = CAPTION_TABLE_RE.match(paragraph)
    if mt:
        num = int(mt.group(1)); dash = mt.group(2); title = (mt.group(3) or "").strip()
        if dash != '—':
            issues.append(Issue(idx, paragraph.find(dash), 1, SEVERITY_ERROR, CATEGORY['CAPTION'], RID['CAPTION_DASH'],
                                "В подписи таблицы требуется длинное тире «—» с пробелами",
                                context_slice(paragraph, paragraph.find(dash)),
                                [f"Таблица {num} — {title}".strip()]))
        else:
            if not re.search(rf'\bТаблица\s+{num}\s+—\s+', paragraph):
                issues.append(Issue(idx, paragraph.find('—'), 1, SEVERITY_WARN, CATEGORY['CAPTION'], RID['CAPTION_DASH_SPACING'],
                                    "Отсутствуют пробелы вокруг «—»", context_slice(paragraph, paragraph.find('—')),
                                    [f"Таблица {num} — {title}".strip()]))
        if not title:
            issues.append(Issue(idx, 0, 1, SEVERITY_ERROR, CATEGORY['CAPTION'], RID['TABLE_NO_TITLE'],
                                "Отсутствует наименование таблицы", context_slice(paragraph, 0)))
    mf = CAPTION_FIG_RE.match(paragraph)
    if mf:
        num = int(mf.group(2)); dash = mf.group(3); title = (mf.group(4) or "").strip()
        if dash != '—':
            issues.append(Issue(idx, paragraph.find(dash), 1, SEVERITY_ERROR, CATEGORY['CAPTION'], RID['FIG_DASH'],
                                "В подписи рисунка требуется длинное тире «—» с пробелами",
                                context_slice(paragraph, paragraph.find(dash)),
                                [f"{mf.group(1)} {num} — {title}".strip()]))
        else:
            if not re.search(rf'(Рисунок|Рис\.)\s+{num}\s+—\s+', paragraph):
                issues.append(Issue(idx, paragraph.find('—'), 1, SEVERITY_WARN, CATEGORY['CAPTION'], RID['CAPTION_DASH_SPACING'],
                                    "Отсутствуют пробелы вокруг «—»", context_slice(paragraph, paragraph.find('—')),
                                    [f"{mf.group(1)} {num} — {title}".strip()]))
        if not title:
            issues.append(Issue(idx, 0, 1, SEVERITY_ERROR, CATEGORY['CAPTION'], RID['FIG_NO_TITLE'],
                                "Отсутствует наименование рисунка", context_slice(paragraph, 0)))
    return issues

def collect_numbers(paragraph: str, idx: int):
    res = []
    mt = CAPTION_TABLE_RE.match(paragraph)
    if mt:
        res.append(("table", idx, int(mt.group(1))))
    mf = CAPTION_FIG_RE.match(paragraph)
    if mf:
        res.append(("figure", idx, int(mf.group(2))))
    return res

def numbering_issues(items, scope="global"):
    issues: List[Issue] = []
    last_table = None
    last_figure = None
    for kind, idx, num in items:
        if kind == "table":
            if last_table is not None and num != last_table + 1:
                issues.append(Issue(idx, 0, 1, "ошибка", CATEGORY['CAPTION'], RID['TABLE_NUMBER_SEQUENCE'],
                                    f"Нарушена последовательность нумерации таблиц: ожидалась {last_table+1}, а получена {num}", ""))
            last_table = num
        else:
            if last_figure is not None and num != last_figure + 1:
                issues.append(Issue(idx, 0, 1, "ошибка", CATEGORY['CAPTION'], RID['FIG_NUMBER_SEQUENCE'],
                                    f"Нарушена последовательность нумерации рисунков: ожидалась {last_figure+1}, а получена {num}", ""))
            last_figure = num
    seen_t, seen_f = set(), set()
    for kind, idx, num in items:
        if kind == "table":
            if num in seen_t:
                issues.append(Issue(idx, 0, 1, "ошибка", CATEGORY['CAPTION'], RID['TABLE_NUMBER_DUPLICATE'],
                                    f"Номер таблицы {num} используется повторно", ""))
            seen_t.add(num)
        else:
            if num in seen_f:
                issues.append(Issue(idx, 0, 1, "ошибка", CATEGORY['CAPTION'], RID['FIG_NUMBER_DUPLICATE'],
                                    f"Номер рисунка {num} используется повторно", ""))
            seen_f.add(num)
    return issues
