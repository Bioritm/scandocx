
from typing import List, Dict, Tuple
from datetime import datetime
import os, json
from .issue import Issue

def write_reports(src_path: str, issues: List[Issue], by_category: Dict[str,int]) -> Tuple[str,str, int,int,bool]:
    basename = os.path.splitext(os.path.basename(src_path))[0]
    dirpath = os.path.dirname(os.path.abspath(src_path))
    checked_at = datetime.utcnow().isoformat(timespec='seconds') + "Z"
    total = len(issues)
    errors = sum(1 for i in issues if i.severity == "ошибка")
    warnings = sum(1 for i in issues if i.severity == "предупреждение")
    gate_pass = (errors == 0)
    cats = ", ".join([f"{k}: {by_category.get(k,0)}" for k in by_category])
    rep_lines = [
        f"Файл: {basename}",
        f"Дата проверки: {checked_at}",
        f"Замечаний всего: {total}",
        f"По категориям: {cats}",
        ""
    ]
    for n, i in enumerate(issues, 1):
        sev = "ОШИБКА" if i.severity == "ошибка" else "ПРЕДУПРЕЖДЕНИЕ"
        rep_lines.append(f"{n}. [{sev}][{i.category}][{i.rule_id}] @ абз.{i.para_index}:{i.offset}")
        rep_lines.append(f"   Сообщение: {i.message}")
        rep_lines.append(f"   Контекст: …{i.context}…")
        if i.replacements:
            rep_lines.append(f"   Замены: {', '.join(i.replacements)}")
        rep_lines.append("")
    rep_lines.append("Примечания:")
    rep_lines.append("— Параллельная обработка включена; орфография управляется конфигом settings.json.")
    rep_text = "\n".join(rep_lines)
    rep_path = os.path.join(dirpath, f"{basename}.rep")
    with open(rep_path, "w", encoding="utf-8") as f:
        f.write(rep_text)
    issues_json = [{
        "para_index": i.para_index,
        "offset": i.offset,
        "length": i.length,
        "severity": i.severity,
        "category": i.category,
        "rule_id": i.rule_id,
        "message": i.message,
        "context": i.context,
        "replacements": i.replacements
    } for i in issues]
    repj = {
        "version": "GOST-21_34-PLUS",
        "file": basename,
        "checked_at": checked_at,
        "issues_total": total,
        "issues_by_category": by_category,
        "gate": { "errors": errors, "warnings": warnings, "pass": gate_pass },
        "issues": issues_json
    }
    repj_path = os.path.join(dirpath, f"{basename}.rep.json")
    with open(repj_path, "w", encoding="utf-8") as f:
        json.dump(repj, f, ensure_ascii=False, indent=2)
    return rep_path, repj_path, errors, warnings, gate_pass
