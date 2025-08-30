
import argparse, os, sys, glob
from .core.config import load_all
from .core.engine import analyze_file
from .core.reporting import write_reports
from .core.watcher import watch_folder

def do_check(paths, cfg_root=None, recursive=False):
    cfg = load_all(cfg_root)
    files = []
    for p in paths:
        if os.path.isdir(p):
            if recursive:
                for ext in ("*.docx","*.txt"):
                    files.extend(glob.glob(os.path.join(p, "**", ext), recursive=True))
            else:
                for ext in ("*.docx","*.txt"):
                    files.extend(glob.glob(os.path.join(p, ext)))
        else:
            files.append(p)
    if not files:
        print("Нет файлов для проверки")
        return 1
    rc = 0
    for f in files:
        try:
            issues, by_cat = analyze_file(f, cfg)
            rep, repj, errors, warnings, gate = write_reports(f, issues, by_cat)
            print(f"[OK] {f} ⇒ {rep} / {repj} | Ошибок: {errors}; Предупреждений: {warnings}; gate: {'PASS' if gate else 'BLOCK'}")
            if errors:
                rc = 2
        except Exception as e:
            print(f"[ERR] {f}: {e}")
            rc = 3
    return rc

def main():
    import sys, argparse
    from multiprocessing import freeze_support

    # 1) поддержка frozen-приложений (PyInstaller + multiprocessing)
    freeze_support()

    # 2) санитизация argv: игнорируем внутренние аргументы PyInstaller/MP
    bad_prefixes = ("parent_pid=", "--multiprocessing", "--pyi-")
    sys.argv = [sys.argv[0]] + [a for a in sys.argv[1:] if not any(a.startswith(p) for p in bad_prefixes)]

    ap = argparse.ArgumentParser(prog="gost-precheck", description="GOST 2.105/34 precheck (high-performance)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_check = sub.add_parser("check", help="Проверить файлы или папки")
    ap_check.add_argument("paths", nargs="+", help="Файлы .docx/.txt или папки")
    ap_check.add_argument("--config", help="Папка с конфигами JSON", default=None)
    ap_check.add_argument("--recursive", action="store_true", help="Рекурсивно обходить папку")

    ap_watch = sub.add_parser("watch", help="Следить за папкой и проверять новые/измененные файлы")
    ap_watch.add_argument("folder", help="Папка для наблюдения")
    ap_watch.add_argument("--config", help="Папка с конфигами JSON", default=None)
    ap_watch.add_argument("--interval", type=float, default=2.0, help="Интервал опроса (сек)")

    args, _unknown = ap.parse_known_args()  # на всякий случай терпим неизвестные
    if args.cmd == "check":
        sys.exit(do_check(args.paths, cfg_root=args.config, recursive=args.recursive))
    elif args.cmd == "watch":
        # ленивый импорт чтобы не тащить watcher в дочерние процессы
        from .core.config import load_all
        from .core.engine import analyze_file
        from .core.reporting import write_reports
        from .core.watcher import watch_folder
        cfg = load_all(args.config)
        def on_file(path):
            if not path.lower().endswith((".docx",".txt")):
                return
            try:
                issues, by_cat = analyze_file(path, cfg)
                rep, repj, errors, warnings, gate = write_reports(path, issues, by_cat)
                print(f"[WATCH] {path} ⇒ {rep} / {repj} | Ошибок: {errors}; Предупреждений: {warnings}; gate: {'PASS' if gate else 'BLOCK'}")
            except Exception as e:
                print(f"[WATCH-ERR] {path}: {e}")
        print(f"Наблюдение за {args.folder} (интервал {args.interval}s) ...")
        watch_folder(args.folder, on_file, interval=args.interval)
