
from typing import List, Dict
from ..issue import Issue
from ..constants import CATEGORY, SEVERITY_ERROR
from ..utils import context_slice
import re

def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    issues: List[Issue] = []
    for rule in cfg["brands"]["rules"]:
        pattern = re.compile(rule["pattern"], flags=re.IGNORECASE if rule.get("ignore_case", True) else 0)
        for m in pattern.finditer(paragraph):
            if "http://" in paragraph or "https://" in paragraph:
                continue
            issues.append(Issue(idx, m.start(), len(m.group()), SEVERITY_ERROR, CATEGORY['BRAND'], rule["rule_id"],
                                f"Используйте «{rule['good']}»", context_slice(paragraph, m.start()), [rule["good"]]))
    return issues
