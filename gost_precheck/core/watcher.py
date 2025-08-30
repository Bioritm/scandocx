
import os, time
from typing import Callable

def watch_folder(path: str, on_file: Callable[[str], None], patterns=(".docx",".txt"), interval=2.0):
    seen = {}
    path = os.path.abspath(path)
    while True:
        for entry in os.scandir(path):
            if not entry.is_file():
                continue
            if not entry.name.lower().endswith(patterns):
                continue
            stat = entry.stat()
            key = entry.path
            mtime = stat.st_mtime
            if key not in seen or seen[key] < mtime:
                seen[key] = mtime
                on_file(key)
        time.sleep(interval)
