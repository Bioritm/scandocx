# gui_client.py
import os, threading, queue, traceback
from tkinter import Tk, StringVar, BooleanVar, filedialog, messagebox
from tkinter import ttk

from gost_precheck.core.config import load_all
from gost_precheck.core.engine import analyze_file

APP_TITLE = "gost-precheck — Desktop"
DEFAULT_CFG = os.path.join(os.path.dirname(__file__), "gost_precheck", "config_full")

class App:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1000x660")

        top = ttk.Frame(root, padding=8); top.pack(side="top", fill="x")
        self.cfg_dir = StringVar(value=DEFAULT_CFG)
        ttk.Label(top, text="Профиль:").pack(side="left")
        ttk.Entry(top, width=60, textvariable=self.cfg_dir).pack(side="left", padx=4)
        ttk.Button(top, text="Выбрать…", command=self.pick_cfg).pack(side="left", padx=4)

        self.recursive = BooleanVar(value=False)
        ttk.Checkbutton(top, text="Рекурсивно", variable=self.recursive).pack(side="left", padx=10)
        ttk.Button(top, text="Файлы…", command=self.pick_files).pack(side="left", padx=4)
        ttk.Button(top, text="Папка…", command=self.pick_folder).pack(side="left", padx=4)
        ttk.Button(top, text="Пуск", command=self.run).pack(side="left", padx=12)

        stat = ttk.Frame(root, padding=(8,0,8,0)); stat.pack(side="top", fill="x")
        self.status = StringVar(value="Готово.")
        self.progress = ttk.Progressbar(stat, mode="determinate", maximum=100)
        self.progress.pack(side="right", fill="x", expand=True, padx=4)
        ttk.Label(stat, textvariable=self.status).pack(side="left")

        center = ttk.Frame(root, padding=8); center.pack(side="top", fill="both", expand=True)
        cols = ("file","severity","category","rule","para","offset","message","context")
        self.tree = ttk.Treeview(center, columns=cols, show="headings", height=22)
        for c, w in [("file",200),("severity",100),("category",150),("rule",160),
                     ("para",60),("offset",60),("message",360),("context",320)]:
            self.tree.heading(c, text=c); self.tree.column(c, width=w, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        vsb = ttk.Scrollbar(center, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y"); self.tree.configure(yscrollcommand=vsb.set)

        bottom = ttk.Frame(root, padding=8); bottom.pack(side="bottom", fill="x")
        ttk.Button(bottom, text="Открыть .rep/.json", command=self.open_reports).pack(side="left")
        ttk.Button(bottom, text="Открыть папку", command=self.open_dir).pack(side="left", padx=6)
        ttk.Button(bottom, text="Очистить", command=self.clear_all).pack(side="right")

        self.files = []
        self.q = queue.Queue()
        self.worker = None

    def pick_cfg(self):
        d = filedialog.askdirectory(initialdir=self.cfg_dir.get() or ".", title="Папка с settings.json")
        if d: self.cfg_dir.set(d)

    def pick_files(self):
        paths = filedialog.askopenfilenames(
            filetypes=[("Docs","*.docx;*.txt"),("DOCX","*.docx"),("TXT","*.txt"),("All","*.*")]
        )
        if paths:
            self.files.extend(list(paths))
            self.status.set(f"Добавлено файлов: {len(paths)} (всего {len(self.files)})")

    def pick_folder(self):
        d = filedialog.askdirectory(title="Папка с документами")
        if not d: return
        if self.recursive.get():
            for root, _dirs, files in os.walk(d):
                for name in files:
                    if name.lower().endswith((".docx",".txt")):
                        self.files.append(os.path.join(root, name))
        else:
            for name in os.listdir(d):
                p = os.path.join(d, name)
                if os.path.isfile(p) and name.lower().endswith((".docx",".txt")):
                    self.files.append(p)
        self.status.set(f"Добавлено из папки. Всего файлов: {len(self.files)}")

    def run(self):
        if not self.files:
            messagebox.showinfo(APP_TITLE, "Добавьте .docx/.txt")
            return
        cfg_root = self.cfg_dir.get().strip()
        if not os.path.isfile(os.path.join(cfg_root, "settings.json")):
            messagebox.showerror(APP_TITLE, f"В {cfg_root} нет settings.json")
            return
        for item in self.tree.get_children(): self.tree.delete(item)
        self.progress["value"] = 0; self.status.set("Загрузка конфига…")
        try:
            cfg = load_all(cfg_root)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Ошибка конфига:\n{e}")
            return
        self.worker = threading.Thread(target=self._worker_run, args=(list(self.files), cfg), daemon=True)
        self.worker.start()
        self.root.after(100, self._pump_q)

    def _worker_run(self, files, cfg):
        total = len(files); done = 0
        for fpath in files:
            try:
                issues, by_cat, debug_meta = analyze_file(fpath, cfg)
                for i in issues:
                    self.q.put(("row", fpath, i))
                errors = sum(1 for i in issues if i.severity == "ошибка")
                warnings = sum(1 for i in issues if i.severity == "предупреждение")
                self.q.put(("meta", f"[{os.path.basename(fpath)}] ошибок: {errors}; предупреждений: {warnings}"))
            except Exception as e:
                self.q.put(("meta", f"[ERR] {fpath}: {e}"))
                traceback.print_exc()
            done += 1; self.q.put(("progress", int(done*100/total)))
        self.q.put(("done",""))

    def _pump_q(self):
        import queue as _q
        try:
            while True:
                kind, *payload = self.q.get_nowait()
                if kind == "row":
                    fpath, i = payload
                    self.tree.insert("", "end", values=(
                        os.path.basename(fpath), i.severity, i.category, i.rule_id,
                        i.para_index, i.offset, i.message, i.context
                    ))
                elif kind == "meta":
                    self.status.set(payload[0])
                elif kind == "progress":
                    self.progress["value"] = payload[0]
                elif kind == "done":
                    self.status.set("Готово.")
        except _q.Empty:
            pass
        if self.worker and self.worker.is_alive():
            self.root.after(100, self._pump_q)

    def open_reports(self):
        sel = self.tree.focus()
        if not sel: return
        fname = self.tree.item(sel, "values")[0]
        full = next((p for p in self.files if os.path.basename(p)==fname), None)
        if not full: return
        base, _ = os.path.splitext(full)
        for ext in (".rep",".rep.json"):
            rp = base + ext
            if os.path.exists(rp): os.startfile(rp)

    def open_dir(self):
        sel = self.tree.focus()
        if not sel: return
        fname = self.tree.item(sel, "values")[0]
        full = next((p for p in self.files if os.path.basename(p)==fname), None)
        if full: os.startfile(os.path.dirname(full))

    def clear_all(self):
        self.files.clear()
        for item in self.tree.get_children(): self.tree.delete(item)
        self.progress["value"] = 0
        self.status.set("Готово.")

def main():
    root = Tk()
    try:
        from tkinter import font
        font.nametofont("TkDefaultFont").configure(size=10)
    except Exception:
        pass
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
