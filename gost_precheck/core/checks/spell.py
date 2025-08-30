from typing import List, Dict
from ..issue import Issue
from ..constants import CATEGORY, RID, SEVERITY_ERROR
from ..utils import context_slice
import re

def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    settings = cfg["settings"].get("spell", {})
    if not settings.get("enabled", False):
        return []

    # --- читаем набор языков из настроек; по умолчанию только русский ---
    langs = settings.get("langs", ["ru_RU"])

    try:
        import enchant
    except Exception:
        return []

    issues: List[Issue] = []

    # инициализируем только те словари, что реально нужны
    ru = enchant.Dict("ru_RU") if "ru_RU" in langs else None
    en = enchant.Dict("en_US") if "en_US" in langs else None

    wl = set(cfg.get("ignore", {}).get("spell_whitelist", []))

    # слова: RU/EN, допускаем дефис внутри
    for m in re.finditer(r"[A-Za-zА-Яа-яЁё]+(?:-[A-Za-zА-Яа-яЁё]+)?", paragraph):
        w = m.group(0)
        if w in wl:
            continue
        if len(w) <= settings.get("min_len", 3) or (settings.get("skip_upper", True) and w.isupper()):
            continue

        # если есть кириллица — проверяем русским (если включён), иначе — английским (если включён)
        if re.search(r"[А-Яа-яЁё]", w):
            d = ru; lid = RID["SPELL_RU"]
        else:
            d = en; lid = RID["SPELL_EN"]

        # язык отключён → пропускаем
        if not d:
            continue

        if not d.check(w):
            repl = []
            if settings.get("suggestions", False):
                try:
                    sug = d.suggest(w)
                    if sug:
                        repl = sug[: settings.get("max_suggestions_per_word", 3)]
                except Exception:
                    pass
            issues.append(Issue(
                idx, m.start(), len(w), SEVERITY_ERROR, CATEGORY["SPELL"], lid,
                "Возможная орфографическая ошибка", context_slice(paragraph, m.start()), repl
            ))
    return issues
