# gui_client.py
import os
import sys
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

# Поддержка frozen-приложений (PyInstaller + multiprocessing)
try:
    from multiprocessing import freeze_support
    freeze_support()
except Exception:
    pass

# Чистые импорты нашей библиотеки
from gost_precheck.core.config import load_all
from gost_precheck.core.engine import analyze_file
from gost_precheck.core.reporting import write_reports

APP_TITLE = "gost-precheck — Desktop"
APP_VERSION = "GOST-21_34-PLUS"

# --- вспомогалки -------------------------------------------------------------

def _enumerate_targets(paths, recursive: bool):
    out = []
    for p in paths:
        if os.path.isdir(p):
            patterns = ("*.docx", "*.txt")
            if recursive:
                for pat in patterns:
                    for root, _, files in os.walk(p):
                        out.extend(os.path.join(root, f) for f in files if f.lower().endswith(pat[1:]))
            else:
                for pat in patterns:
                    out.extend(os.path.join(p, f) for f in os.listdir(p) if f.lower().endswith(pat[1:]))
        else:
            out.append(p)
    # убирать дубликаты, сохраняем порядок
    seen = set()
    uniq = []
    for f in out:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq

def _human_profile_path(p):
    try:
        return p if not getattr(sys, "frozen", False) else p.replace(os.environ.get("TEMP",""), r"%TEMP%")
    except Exception:
        return p

# --- GUI ---------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE}")
        self.geometry("1200x560")

        self.cfg_root = os.path.join(os.path.dirname(__file__), "gost_precheck", "config_full")
        self.recursive_var = tk.BooleanVar(value=False)

        self._build_toolbar()
        self._build_table()
        self._build_footer()

        self.q = queue.Queue()
        self.worker = None

    def _build_toolbar(self):
        frm = ttk.Frame(self)
        frm.pack(fill="x", padx=6, pady=4)

        ttk.Label(frm, text="Профиль:").pack(side="left")
        self.profile_lbl_var = tk.StringVar(value=_human_profile_path(self.cfg_root))
        self.profile_lbl = ttk.Entry(frm, textvariable=self.profile_lbl_var, width=80)
        self.profile_lbl.pack(side="left", padx=6)

        ttk.Button(frm, text="Выбрать...", command=self.on_choose_profile).pack(side="left", padx=4)

        self.rec_chk = ttk.Checkbutton(frm, text="Рекурсивно", variable=self.recursive_var)
        self.rec_chk.pack(side="left", padx=8)

        ttk.Button(frm, text="Файлы...", command=self.on_files).pack(side="left", padx=4)
        ttk.Button(frm, text="Папка...", command=self.on_folder).pack(side="left", padx=4)
        ttk.Button(frm, text="Пуск", command=self.on_run).pack(side="left", padx=12)

        self.pb = ttk.Progressbar(frm, mode="determinate")
        self.pb.pack(side="left", fill="x", expand=True, padx=10)
        self.status = ttk.Label(frm, text="Готово.")
        self.status.pack(side="left", padx=4)

        self.targets = []  # выбранные объекты

    def _build_table(self):
        cols = ("file","severity","category","rule","para","offset","message","context")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        self.tree.pack(fill="both", expand=True, padx=6, pady=4)

        headers = {
            "file": "file",
            "severity": "severity",
            "category": "category",
            "rule": "rule",
            "para": "para",
            "offset": "offset",
            "message": "message",
            "context": "context",
        }
        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=120 if c!="context" else 600, anchor="w", stretch=True)
        self.tree.column("para", width=60, anchor="center")
        self.tree.column("offset", width=60, anchor="center")

        # контекстное меню
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Открыть .rep/.json", command=self.on_open_report)
        self.menu.add_command(label="Открыть папку", command=self.on_open_folder)
        self.tree.bind("<Button-3>", self._popup)

    def _build_footer(self):
        frm = ttk.Frame(self)
        frm.pack(fill="x", padx=6, pady=6)
        ttk.Button(frm, text="Открыть .rep/.json", command=self.on_open_report).pack(side="left")
        ttk.Button(frm, text="Открыть папку", command=self.on_open_folder).pack(side="left", padx=6)
        ttk.Button(frm, text="Очистить", command=self.on_clear).pack(side="right")

    # ---- события -------------------------------------------------------------

    def on_choose_profile(self):
        p = filedialog.askdirectory(title="Папка с конфигами JSON (settings.json, abbr.json, ...)")
        if p:
            self.cfg_root = p
            self.profile_lbl_var.set(_human_profile_path(p))

    def on_files(self):
        files = filedialog.askopenfilenames(
            title="Выберите файлы .docx/.txt",
            filetypes=(("DOCX/TXT","*.docx *.txt"), ("Все файлы","*.*")),
        )
        if files:
            self.targets = list(files)
            self.status["text"] = f"Выбрано файлов: {len(self.targets)}"

    def on_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку")
        if folder:
            self.targets = [folder]
            self.status["text"] = f"Выбрана папка: {folder}"

    def on_clear(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

    def _popup(self, event):
        try:
            self.tree.selection_set(self.tree.identify_row(event.y))
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def on_open_report(self):
        sel = self.tree.selection()
        if not sel:
            return
        file_path = self.tree.set(sel[0], "file")
        base, _ = os.path.splitext(file_path)
        rep = base + ".rep"
        repj = base + ".rep.json"
        for p in (rep, repj):
            if os.path.exists(p):
                try:
                    os.startfile(p)  # Windows
                except Exception:
                    messagebox.showinfo("Открыть", p)

    def on_open_folder(self):
        sel = self.tree.selection()
        if not sel:
            return
        file_path = self.tree.set(sel[0], "file")
        folder = os.path.dirname(file_path)
        try:
            os.startfile(folder)
        except Exception:
            messagebox.showinfo("Папка", folder)

    def on_run(self):
        if not self.targets:
            messagebox.showwarning("Нет входных", "Выберите файлы или папку")
            return
        cfg_root = self.cfg_root
        try:
            cfg = load_all(cfg_root)
        except Exception as e:
            messagebox.showerror("Конфиг", f"Не удалось загрузить конфиг из:\n{cfg_root}\n\n{e}")
            return

        files = _enumerate_targets(self.targets, self.recursive_var.get())
        if not files:
            messagebox.showwarning("Нет файлов", "Файлы .docx/.txt не найдены")
            return

        self.on_clear()
        self.pb.configure(maximum=len(files), value=0)
        self.status["text"] = "Работаю…"

        # запускаем в отдельном потоке, UI не замораживаем
        def worker():
            for ix, path in enumerate(files, 1):
                try:
                    issues, by_cat, debug_meta = analyze_file(path, cfg)
                    # гейт
                    errors = sum(1 for i in issues if i.severity == "ошибка")
                    warnings = sum(1 for i in issues if i.severity == "предупреждение")
                    gate = {"errors": errors, "warnings": warnings, "pass": errors == 0}
                    write_reports(path, issues, by_cat, gate, APP_VERSION, debug_meta)

                    if not issues:
                        # всё равно показать строчку-резюме
                        self.q.put(("row", (path, "—", "—", "—", "", "", "Нет замечаний", "")))
                    else:
                        for it in issues:
                            self.q.put(("row", (
                                path,
                                it.severity,
                                it.category,
                                it.rule_id,
                                it.para_index,
                                it.offset,
                                it.message,
                                it.context
                            )))
                except Exception as e:
                    self.q.put(("row", (path, "ошибка", "внутренняя", "EXC", "", "", str(e), "")))
                finally:
                    self.q.put(("tick", None))

            self.q.put(("done", None))

        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Выполняется", "Задача ещё идёт")
            return

        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()
        self.after(50, self._pump_queue)

    def _pump_queue(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "row":
                    self.tree.insert("", "end", values=payload)
                elif kind == "tick":
                    self.pb["value"] = min(self.pb["value"] + 1, self.pb["maximum"])
                elif kind == "done":
                    self.status["text"] = f"Готово. {datetime.now().strftime('%H:%M:%S')}"
        except queue.Empty:
            pass
        if self.worker and self.worker.is_alive():
            self.after(50, self._pump_queue)

if __name__ == "__main__":
    app = App()
    app.mainloop()
