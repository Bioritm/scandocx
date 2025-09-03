# gost_precheck/cli.py
from __future__ import annotations

import os
import sys
import glob
import argparse
from typing import Dict, Iterable, List, Tuple

from .core.config import load_all
from .core.engine import analyze_file
from .core.reporting import write_reports
from .core.watcher import watch_folder

try:
    from .core.constants import VERSION as APP_VERSION
except Exception:
    APP_VERSION = "GOST-21_34-PLUS"


# ------------------------------- utils --------------------------------- #

def _fmt_loader_debug(stats: dict, file_hint: str = "") -> str:
    # stats может содержать parts как int или как list — поддержим оба
    parts_obj = stats.get("parts", [])
    try:
        parts_count = len(parts_obj)  # если это список
    except TypeError:
        # если это уже число или None
        parts_count = int(parts_obj or 0)

    return (
        f"[DEBUG] docx: "
        f"p_total={stats.get('p_total', 0)} "
        f"kept={stats.get('kept', 0)} "
        f"blank={stats.get('blank', 0)} "
        f"w:t={stats.get('wt', 0)} "
        f"instr={stats.get('instr', 0)} "
        f"del={stats.get('deleted', 0)} "
        f"tabs={stats.get('tabs', 0)} "
        f"br={stats.get('br', 0)} "
        f"parts={parts_count}"
        + (f"  file: {os.path.basename(file_hint)}" if file_hint else "")
    )



def _enumerate_targets(paths: Iterable[str], recursive: bool) -> List[str]:
    files: List[str] = []
    patterns = ("*.docx", "*.txt")
    for p in paths:
        # поддержка «масок» прямо в аргументах: *.docx и т.п.
        if any(ch in p for ch in "*?[]"):
            files.extend(glob.glob(p, recursive=recursive))
            continue

        if os.path.isdir(p):
            if recursive:
                for ext in patterns:
                    files.extend(glob.glob(os.path.join(p, "**", ext), recursive=True))
            else:
                for ext in patterns:
                    files.extend(glob.glob(os.path.join(p, ext)))
        else:
            files.append(p)
    # уникализируем и стабильно сортируем
    return sorted(dict.fromkeys(files))


def _calc_gate(issues) -> Dict:
    errors = sum(1 for i in issues if getattr(i, "severity", "") == "ошибка")
    warnings = sum(1 for i in issues if getattr(i, "severity", "") == "предупреждение")
    return {"errors": errors, "warnings": warnings, "pass": errors == 0}


# ------------------------------ commands -------------------------------- #

def do_check(paths, cfg_root=None, recursive=False, debug=False) -> int:
    cfg = load_all(cfg_root)
    files = _enumerate_targets(paths, recursive)

    if not files:
        print("Нет файлов для проверки")
        return 4  # «no input»

    rc = 0
    for f in files:
        try:
            issues, by_cat, debug_meta = analyze_file(f, cfg)
            gate = _calc_gate(issues)

            # пишем отчёты (.rep / .rep.json)
            write_reports(f, issues, by_cat, gate, APP_VERSION, debug_meta)

            base, _ = os.path.splitext(f)
            rep, repj = base + ".rep", base + ".rep.json"
            print(
                f"[OK] {f} ⇒ {rep} / {repj} | "
                f"Ошибок: {gate['errors']}; Предупреждений: {gate['warnings']}; "
                f"gate: {'PASS' if gate['pass'] else 'BLOCK'}"
            )

            # Печать диагностической сводки по загрузчику:
            loader_stats = (debug_meta or {}).get("loader_stats", {})
            if debug or loader_stats.get("kept", 0) == 0:
                print(_fmt_loader_debug(loader_stats, file_hint=f))

            if gate["errors"]:
                rc = 2  # есть ошибки правил

        except Exception as e:
            print(f"[ERR] {f}: {e}")
            rc = 3  # внутренняя ошибка

    return rc


def do_watch(folder: str, cfg_root=None, interval: float = 2.0, debug=False) -> None:
    cfg = load_all(cfg_root)

    def on_file(path: str):
        if not path.lower().endswith((".docx", ".txt")):
            return
        try:
            issues, by_cat, debug_meta = analyze_file(path, cfg)
            gate = _calc_gate(issues)
            write_reports(path, issues, by_cat, gate, APP_VERSION, debug_meta)

            base, _ = os.path.splitext(path)
            rep, repj = base + ".rep", base + ".rep.json"
            print(
                f"[WATCH] {path} ⇒ {rep} / {repj} | "
                f"Ошибок: {gate['errors']}; Предупреждений: {gate['warnings']}; "
                f"gate: {'PASS' if gate['pass'] else 'BLOCK'}"
            )

            if debug or (debug_meta.get("loader_stats", {}).get("kept", 0) == 0):
                print(_fmt_loader_debug(debug_meta.get("loader_stats", {}), file_hint=path))

        except Exception as e:
            print(f"[WATCH-ERR] {path}: {e}")

    print(f"Наблюдение за {folder} (интервал {interval}s) …")
    watch_folder(folder, on_file, interval=interval)


def do_terms(paths: Iterable[str], recursive: bool, out_json: str, out_csv: str) -> int:
    """
    Лёгкий сборщик терминов/акронимов (если модуль terms присутствует).
    """
    try:
        from .core.terms import scan_files, write_terms_json_csv  # ленивый импорт
    except Exception as e:
        print(f"[TERMS] модуль недоступен: {e}")
        return 5

    files = _enumerate_targets(paths, recursive)
    if not files:
        print("Нет файлов для извлечения терминов")
        return 4

    bank = scan_files(files, cfg=None)  # жёсткая загрузка без фильтров
    write_terms_json_csv(bank, out_json, out_csv)
    print(f"[TERMS] собрано терминов: {len(bank)} → {out_json}, {out_csv}")
    return 0


# -------------------------------- main ---------------------------------- #

def main():
    from multiprocessing import freeze_support

    # поддержка frozen-приложений (PyInstaller + multiprocessing)
    freeze_support()

    # санитизация argv: убираем внутренние аргументы PyInstaller/MP
    bad_prefixes = ("parent_pid=", "--multiprocessing", "--pyi-")
    sys.argv = [sys.argv[0]] + [
        a for a in sys.argv[1:] if not any(a.startswith(p) for p in bad_prefixes)
    ]

    ap = argparse.ArgumentParser(
        prog="gost-precheck",
        description=f"GOST 2.105/34 precheck (v{APP_VERSION}, high-performance, offline)"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    # check
    ap_check = sub.add_parser("check", help="Проверить файлы или папки (.docx/.txt)")
    ap_check.add_argument("paths", nargs="+", help="Файлы/папки/маски (*.docx, *.txt)")
    ap_check.add_argument("--config", help="Папка с конфигами JSON (профиль)", default=None)
    ap_check.add_argument("--recursive", action="store_true", help="Рекурсивно обходить папки")
    ap_check.add_argument("--debug", action="store_true", help="Диагностика loader/внутр.ошибок")

    # watch
    ap_watch = sub.add_parser("watch", help="Следить за папкой и проверять изменения")
    ap_watch.add_argument("folder", help="Папка для наблюдения")
    ap_watch.add_argument("--config", help="Папка с конфигами JSON (профиль)", default=None)
    ap_watch.add_argument("--interval", type=float, default=2.0, help="Интервал опроса (сек)")
    ap_watch.add_argument("--debug", action="store_true", help="Диагностика loader/внутр.ошибок")

    # terms
    ap_terms = sub.add_parser("terms", help="Извлечь термины/сокращения из документов")
    ap_terms.add_argument("paths", nargs="+", help="Файлы/папки/маски (*.docx, *.txt)")
    ap_terms.add_argument("--recursive", action="store_true", help="Рекурсивно обходить папки")
    ap_terms.add_argument("--out", default="terms.json", help="JSON-вывод (банк терминов)")
    ap_terms.add_argument("--out-csv", default="terms.csv", help="CSV-вывод (для Excel)")

    args, _unknown = ap.parse_known_args()

    if args.cmd == "check":
        sys.exit(do_check(args.paths, cfg_root=args.config, recursive=args.recursive, debug=args.debug))

    if args.cmd == "watch":
        do_watch(args.folder, cfg_root=args.config, interval=args.interval, debug=args.debug)
        return

    if args.cmd == "terms":
        sys.exit(do_terms(args.paths, recursive=args.recursive, out_json=args.out, out_csv=args.out_csv))


if __name__ == "__main__":
    main()
