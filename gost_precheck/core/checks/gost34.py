
from typing import List, Dict
from ..issue import Issue
from ..constants import CATEGORY, SEVERITY_ERROR
from ..utils import context_slice
import re

def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    issues: List[Issue] = []
    if "http://" in paragraph or "https://" in paragraph:
        return issues
    for rule in cfg["gost34"]["rules"]:
        pattern = re.compile(rule["pattern"])
        for m in pattern.finditer(paragraph):
            issues.append(Issue(idx, m.start(), len(m.group()), SEVERITY_ERROR, CATEGORY['GOST34'], rule["rule_id"],
                                f"Устаревшая ссылка — замените на «{rule['good']}»",
                                context_slice(paragraph, m.start()), [rule["good"]]))
    return issues
