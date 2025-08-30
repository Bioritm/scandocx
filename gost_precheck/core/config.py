# gost_precheck/core/config.py
import json, os, sys
from pathlib import Path
from typing import Any, Dict

def _default_config_path() -> Path:
    # Когда запущено из PyInstaller (.exe)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "gost_precheck" / "config"
    # Обычный запуск (исходники/установленный пакет)
    return Path(__file__).resolve().parent.parent / "config"

DEFAULT_CONFIG_PATH = str(_default_config_path())

def read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_all(config_root: str = None) -> Dict[str, Any]:
    root = Path(config_root) if config_root else Path(DEFAULT_CONFIG_PATH)
    return {
        "settings": read_json(str(root / "settings.json")),
        "abbr":     read_json(str(root / "abbr.json")),
        "brands":   read_json(str(root / "brands.json")),
        "gost34":   read_json(str(root / "gost34.json")),
        "ignore":   read_json(str(root / "ignore_patterns.json")),
    }
