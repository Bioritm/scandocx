# gost_precheck/core/reporting.py
from __future__ import annotations
import json, datetime, os
from typing import List, Dict, Iterable
from .issue import Issue

# ---------------- helpers ---------------- #

def _now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _shorten(ctx: str, left: int = 50, right: int = 50) -> str:
    """
    Компактный контекст: обрезаем длинные строки, показываем «…» по краям.
    Никакой типографики тут не делаем — только усечённый preview.
    """
    if ctx is None:
        return ""
    s = ctx.replace("\n", "⏎")
    if len(s) <= left + right + 5:
        return s
    return f"{s[:left]}…{s[-right:]}"

def _severity_rank(sev: str) -> int:
    return {"ошибка": 0, "предупреждение": 1}.get(sev, 9)

def _group_rule_stats(issues: Iterable[Issue]) -> Dict[str, int]:
    """Подсчёт срабатываний по rule_id (для JSON-диагностики)."""
    out: Dict[str, int] = {}
    for i in issues:
        out[i.rule_id] = out.get(i.rule_id, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))

# ---------------- main API ---------------- #

def write_reports(src_path: str,
                  issues: List[Issue],
                  by_category: Dict[str,int],
                  gate: Dict[str, int],
                  version: str,
                  debug_meta: Dict) -> None:
    """
    Пишем два отчёта: <file>.rep и <file>.rep.json.
    - .rep — человекочитаемый краткий отчёт с секциями по категориям.
    - .rep.json — полный, машинный + расширенная диагностика (loader_stats, rule_stats, timing, profile).
    """
    base, _ = os.path.splitext(src_path)
    txt_path = base + ".rep"
    json_path = base + ".rep.json"

    errors = gate.get("errors", 0)
    warnings = gate.get("warnings", 0)
    passed = bool(gate.get("pass", False))

    # ---- .rep (человекочитаемый) ---- #
    # Сортируем стабильно: sever/para/offset/rule
    issues_sorted = sorted(
        issues,
        key=lambda x: (_severity_rank(x.severity), x.para_index, x.offset, x.rule_id)
    )

    # Группируем по категории
    by_cat_list = sorted(by_category.items(), key=lambda kv: (-kv[1], kv[0]))
    cat_to_issues: Dict[str, List[Issue]] = {}
    for i in issues_sorted:
        cat_to_issues.setdefault(i.category, []).append(i)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"Файл: {os.path.basename(src_path)}\n")
        f.write(f"Дата проверки: {_now_iso()}\n")
        f.write(f"Замечаний всего: {len(issues_sorted)}\n")
        if by_cat_list:
            cats_line = "; ".join(f"{k}: {v}" for k, v in by_cat_list)
            f.write(f"По категориям: {cats_line}\n\n")
        else:
            f.write("\n")

        # Секции по категориям (если нет замечаний — заголовки не печатаем)
        idx = 1
        for cat, items in cat_to_issues.items():
            f.write(f"== {cat} ({len(items)}) ==\n")
            for it in items:
                pos = f"абз.{it.para_index}:{it.offset}"
                ctx = _shorten(it.context or "", 60, 60)
                repl = ""
                if it.replacements:
                    # показываем только inline-подсказки, без лишней «шумотехники»
                    repl = " | Замены: " + ", ".join(map(str, it.replacements))
                f.write(
                    f"{idx}. [{it.severity.upper()}][{it.rule_id}] @ {pos}\n"
                    f"   Сообщение: {it.message}\n"
                    f"   Контекст: {ctx}{repl}\n"
                )
                idx += 1
            f.write("\n")

        f.write(
            f"[{'OK' if passed else 'FAIL'}] Ошибок: {errors}; "
            f"Предупреждений: {warnings}; gate: {'PASS' if passed else 'BLOCK'}\n"
        )

    # ---- .rep.json (машинный + диагн.) ---- #
    loader_stats = (debug_meta or {}).get("loader_stats", {})
    timing       = (debug_meta or {}).get("timing", {})           # опционально (если замеряете в engine)
    profile      = (debug_meta or {}).get("profile", None)        # опционально (наименование профиля конфигурации)
    internal_err = (debug_meta or {}).get("internal_errors", [])  # список строк с внутренними исключениями

    payload = {
        "version": version,
        "file": os.path.basename(base),
        "checked_at": _now_iso(),
        "issues_total": len(issues_sorted),
        "issues_by_category": by_category,
        "gate": {
            "errors": errors,
            "warnings": warnings,
            "pass": passed
        },
        "issues": [i.to_dict() for i in issues_sorted],
        "rule_stats": _group_rule_stats(issues_sorted),
        "debug": {
            "loader_stats": loader_stats,     # p_total/kept/blank/wt/instr/deleted/tabs/br/parts[]
            "timing": timing,                 # total_ms/load_ms/regex_ms/spell_ms (если есть)
            "profile": profile,               # имя профиля (fast/full), если проброшено из CLI
            "internal_errors": internal_err   # список внутренних ошибок правил/лоадера/движка
        }
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
