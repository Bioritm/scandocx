
from typing import List, Dict
from ..issue import Issue
from ..constants import CATEGORY, RID, SEVERITY_ERROR, NBSP
from ..utils import context_slice
import re

def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    issues: List[Issue] = []
    for rule in cfg["abbr"]["rules"]:
        pattern = re.compile(rule["pattern"], flags=re.IGNORECASE)
        for m in pattern.finditer(paragraph):
            pos = m.start()
            repl = rule["replacement"]
            repl_nbsp = rule.get("replacement_nbsp", repl.replace(" ", NBSP))
            issues.append(Issue(idx, pos, len(m.group()), SEVERITY_ERROR, CATEGORY['TYPO'], RID['ABBR_SPACING'],
                                "Требуется пробел(ы) в сокращении", context_slice(paragraph, pos),
                                [repl, repl_nbsp]))
    return issues
