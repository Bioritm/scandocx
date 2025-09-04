# gost_precheck/core/checks/captions.py
from typing import List, Dict, Tuple
import re

from ..issue import Issue
from ..constants import CATEGORY, RID, SEVERITY_ERROR, SEVERITY_WARN
from ..utils import context_slice

# "Таблица 1 — Название", "Табл. 1.2 — ...", "Рисунок 3 — ...", "Рис. 2.1 — ..."
RE_CAPTION = re.compile(
    r'^(?P<kind>(Таблица|Табл\.|Рисунок|Рис\.))\s+'
    r'(?P<num>\d+(?:\.\d+)*)'           # 1 / 1.2 / 1.2.3
    r'\s*(?P<dash>[—–-])\s*'            # тире/дефис с произвольными пробелами
    r'(?P<title>.*)$'
)

def _is_table(kind: str) -> bool:
    return kind.startswith("Таб")

def _is_figure(kind: str) -> bool:
    return kind.startswith("Рис")

def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    issues: List[Issue] = []
    text = paragraph.strip()
    m = RE_CAPTION.match(text)
    if not m:
        return issues

    dash = m.group("dash")
    title = (m.group("title") or "")
    title_stripped = title.strip()

    # 1) В подписях — только длинное тире
    if dash != "—":
        pos = text.find(dash)
        issues.append(Issue(
            idx, pos, 1,
            SEVERITY_ERROR, CATEGORY["CAPTIONS"], RID["CAPTION_DASH_EM"],
            "В подписях используйте длинное тире «—»",
            context_slice(paragraph, pos),
            ["—"]
        ))

    # 2) Ровно один пробел по сторонам тире: "N — Название"
    #    Проверим непосредственно окружение символа тире из матча.
    d_s = m.start("dash")
    d_e = m.end("dash")
    left_ok  = (d_s > 0 and text[d_s-1] == " ")
    right_ok = (d_e < len(text) and text[d_e] == " ")
    # запретим множественные пробелы: после нормализации должно совпасть
    normalized = re.sub(r'(\d+(?:\.\d+)*)\s*[—–-]\s*', r'\1 — ', text, count=1)
    spacing_ok = (left_ok and right_ok and normalized == text)
    if not spacing_ok:
        issues.append(Issue(
            idx, d_s, 1,
            SEVERITY_ERROR, CATEGORY["CAPTIONS"], RID["CAPTION_SPACING"],
            "Нужны ровно по одному пробелу по сторонам: «N — Название»",
            context_slice(paragraph, d_s),
            ["N — Название"]
        ))

    # 3) Пустое/пробельное название
    if not title_stripped:
        pos = text.rfind(dash)
        issues.append(Issue(
            idx, max(pos, 0), 1,
            SEVERITY_ERROR, CATEGORY["CAPTIONS"], RID["CAPTION_EMPTY_TITLE"],
            "Отсутствует название после тире",
            context_slice(paragraph, max(pos, 0)),
            []
        ))

    return issues

# Сбор номеров для последующей проверки дубликатов/порядка
def collect_numbers(paragraph: str, idx: int):
    out = []
    text = paragraph.strip()
    m = RE_CAPTION.match(text)
    if not m:
        return out
    kind  = m.group("kind")
    num_s = m.group("num")
    dash  = m.group("dash")
    title = (m.group("title") or "").strip()
    try:
        seq = tuple(int(x) for x in num_s.split("."))
    except Exception:
        seq = (999999,)  # не валим пайплайн
    out.append({
        "idx": idx,
        "kind": "table" if _is_table(kind) else "figure",
        "num": seq,
        "raw": num_s,
        "dash": dash,
        "title": title,
    })
    return out

def numbering_issues(items: List[Dict], scope: str = "global") -> List[Issue]:
    issues: List[Issue] = []
    for kind in ("table", "figure"):
        arr = [x for x in items if x["kind"] == kind]
        if not arr:
            continue

        # 1) Дубликаты
        seen = {}
        for it in arr:
            key = it["num"]
            if key in seen:
                issues.append(Issue(
                    it["idx"], 0, 0,
                    SEVERITY_WARN, CATEGORY["CAPTIONS"], RID["CAPTION_DUPLICATE"],
                    f"Дублируется номер {('Таблица' if kind=='table' else 'Рисунок')} {it['raw']}",
                    "", []
                ))
            else:
                seen[key] = it["idx"]

        # 2) Регресс нумерации по фактическому порядку появления
        prev = None
        for it in arr:     # порядок сохранён как в документе
            if prev is not None and it["num"] < prev:
                issues.append(Issue(
                    it["idx"], 0, 0,
                    SEVERITY_WARN, CATEGORY["CAPTIONS"], RID["CAPTION_ORDER"],
                    f"Нарушен порядок нумерации {('таблиц' if kind=='table' else 'рисунков')}",
                    "", []
                ))
            prev = it["num"]

    return issues
