# gost_precheck/core/issue.py
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Issue:
    para_index: int           # индекс абзаца
    offset: int               # позиция в абзаце (0-based)
    length: int               # длина проблемного фрагмента
    severity: str             # "ошибка" | "предупреждение"
    category: str             # человекочитаемая категория
    rule_id: str              # стабильный ID правила
    message: str              # текст сообщения
    context: str              # срез контекста вокруг ошибки
    replacements: List[str] = field(default_factory=list)  # подсказки/замены
    meta: Dict[str, Any] = field(default_factory=dict)     # произвольные детали

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "para_index": self.para_index,
            "offset": self.offset,
            "length": self.length,
            "severity": self.severity,
            "category": self.category,
            "rule_id": self.rule_id,
            "message": self.message,
            "context": self.context,
            "replacements": self.replacements,
        }
        if self.meta:
            d["meta"] = self.meta
        return d
