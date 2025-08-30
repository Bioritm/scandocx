
from dataclasses import dataclass, field
from typing import List

@dataclass
class Issue:
    para_index: int
    offset: int
    length: int
    severity: str  # "ошибка" | "предупреждение"
    category: str
    rule_id: str
    message: str
    context: str
    replacements: List[str] = field(default_factory=list)
