# -*- coding: utf-8 -*-
from typing import List, Dict
from ..issue import Issue
from ..constants import CATEGORY, RID, SEVERITY_ERROR
from ..regexes import (
    RE_SPACE_BEFORE_PUNCT,
    RE_NO_SPACE_AFTER_PUNCT,
    RE_DOUBLE_COMMA,
    RE_DOUBLE_SEMI,
    RE_DOUBLE_COLON,
    RE_TWO_DOTS,
    RE_MANY_DOTS,
)
from ..utils import context_slice


def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    issues: List[Issue] = []

    # Пробел перед знаком
    for m in RE_SPACE_BEFORE_PUNCT.finditer(paragraph):
        issues.append(
            Issue(
                idx, m.start(), 1, SEVERITY_ERROR,
                CATEGORY["PUNCT"], RID["PUNCT_SPACE_BEFORE"],
                "Лишний пробел перед знаком препинания",
                context_slice(paragraph, m.start()),
                ["убрать пробел перед знаком"],
            )
        )

    # Нет пробела после знака
    for m in RE_NO_SPACE_AFTER_PUNCT.finditer(paragraph):
        pos = m.start()
        issues.append(
            Issue(
                idx, pos, 1, SEVERITY_ERROR,
                CATEGORY["PUNCT"], RID["PUNCT_NO_SPACE_AFTER"],
                "Нет пробела после знака препинания",
                context_slice(paragraph, pos),
                ["добавить пробел после знака"],
            )
        )

    # Двойные знаки
    for m in RE_DOUBLE_COMMA.finditer(paragraph):
        issues.append(
            Issue(
                idx, m.start(), 2, SEVERITY_ERROR,
                CATEGORY["PUNCT"], RID["PUNCT_DOUBLE_COMMA"],
                "Двойная запятая",
                context_slice(paragraph, m.start()),
                [","],
            )
        )
    for m in RE_DOUBLE_SEMI.finditer(paragraph):
        issues.append(
            Issue(
                idx, m.start(), 2, SEVERITY_ERROR,
                CATEGORY["PUNCT"], RID["PUNCT_DOUBLE_SEMI"],
                "Двойная точка с запятой",
                context_slice(paragraph, m.start()),
                [";"],
            )
        )
    for m in RE_DOUBLE_COLON.finditer(paragraph):
        issues.append(
            Issue(
                idx, m.start(), 2, SEVERITY_ERROR,
                CATEGORY["PUNCT"], RID["PUNCT_DOUBLE_COLON"],
                "Двойное двоеточие",
                context_slice(paragraph, m.start()),
                [":"],
            )
        )

    # ".." и "...."
    for m in RE_TWO_DOTS.finditer(paragraph):
        issues.append(
            Issue(
                idx, m.start(), 2, SEVERITY_ERROR,
                CATEGORY["PUNCT"], RID["PUNCT_TWO_DOTS"],
                "Ровно две точки — используйте «…»",
                context_slice(paragraph, m.start()),
                ["…"],
            )
        )
    for m in RE_MANY_DOTS.finditer(paragraph):
        issues.append(
            Issue(
                idx, m.start(), len(m.group()), SEVERITY_ERROR,
                CATEGORY["PUNCT"], RID["PUNCT_MANY_DOTS"],
                "4+ точек — используйте «…»",
                context_slice(paragraph, m.start()),
                ["…"],
            )
        )

    return issues
