# gost_precheck/core/config.py
import json, os
from pathlib import Path
from typing import Any, Dict, List, Set

def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _read_lines(path: Path) -> List[str]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return [ln.strip() for ln in f if ln.strip()]

def load_all(cfg_root: str | None) -> Dict[str, Any]:
    """
    Структура:
      settings.json                        — обязательный
      brands.json / abbr.json / gost34.json — опциональные
      words_custom.json                     — опциональный список "разрешённых" слов (кастом)
      ru_wordlist.txt                       — опциональный словарь для fallback-орфографии
    """
    root = Path(cfg_root) if cfg_root else Path(__file__).resolve().parent.parent / "config"
    if not root.exists():
        raise RuntimeError(f"Папка конфигов не найдена: {root}")

    cfg: Dict[str, Any] = {}
    cfg["__root"] = str(root)

    # обязательный
    cfg["settings"] = _read_json(root / "settings.json")

    # опциональные (если нет — пустые)
    for name in ("brands.json", "abbr.json", "gost34.json"):
        p = root / name
        try:
            cfg[name.removesuffix(".json")] = _read_json(p) if p.exists() else {}
        except Exception as e:
            raise RuntimeError(f"Ошибка чтения {p}: {e}")

    # словари
    words_custom_path = root / "words_custom.json"
    if words_custom_path.exists():
        try:
            wl = _read_json(words_custom_path)
            # допускаем как список строк, так и {"allow": [...]}:
            if isinstance(wl, dict) and "allow" in wl:
                wl = wl["allow"]
            cfg["dict_user_words"] = {w.strip() for w in wl if w and isinstance(w, str)}
        except Exception as e:
            raise RuntimeError(f"Ошибка чтения words_custom.json: {e}")
    else:
        cfg["dict_user_words"] = set()

    ru_wordlist = root / "ru_wordlist.txt"
    cfg["dict_ru_wordlist_path"] = str(ru_wordlist) if ru_wordlist.exists() else None

    return cfg
