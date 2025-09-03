# gost_precheck/core/checks/spell.py
from __future__ import annotations
from typing import List, Dict, Set
import re, os

from ..issue import Issue
from ..constants import CATEGORY, RID, SEVERITY_ERROR
from ..utils import context_slice

# токены: рус/лат буквы + дефис/апостроф, но не числа
TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё\-’']{1,}", re.UNICODE)

# глобалы в процессе (для ProcessPool)
_ENCHANT_READY = False
_ENCHANT_DICT = None
_WORDLIST_CACHE: Set[str] | None = None

def _try_init_enchant(lang: str) -> bool:
    global _ENCHANT_READY, _ENCHANT_DICT
    if _ENCHANT_READY:
        return _ENCHANT_DICT is not None
    try:
        import enchant
        _ENCHANT_DICT = enchant.Dict(lang)
        _ENCHANT_READY = True
        return True
    except Exception:
        _ENCHANT_DICT = None
        _ENCHANT_READY = True
        return False

def _ensure_wordlist(cfg: Dict):
    global _WORDLIST_CACHE
    if _WORDLIST_CACHE is not None:
        return
    p = cfg.get("dict_ru_wordlist_path")
    _WORDLIST_CACHE = set()
    if p and os.path.exists(p):
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            for ln in f:
                w = ln.strip()
                if w:
                    _WORDLIST_CACHE.add(w.lower())

def _is_ok_by_wordlist(word: str, cfg: Dict) -> bool:
    _ensure_wordlist(cfg)
    if not _WORDLIST_CACHE:
        return False
    return word.lower() in _WORDLIST_CACHE

def _user_whitelist(cfg: Dict) -> Set[str]:
    return cfg.get("dict_user_words", set())

def _is_ignorable(tok: str) -> bool:
    # игнор: ALLCAPS аббревиатуры, токены с цифрами, слишком короткие
    if any(ch.isdigit() for ch in tok):
        return True
    if tok.isupper() and len(tok) <= 6:
        return True
    return False

def check(paragraph: str, idx: int, cfg: Dict) -> List[Issue]:
    out: List[Issue] = []
    spell_cfg = cfg.get("settings", {}).get("spell", {})
    if not spell_cfg.get("enabled", False):
        return out

    lang = spell_cfg.get("lang", "ru_RU")
    use_enchant = _try_init_enchant(lang)
    wl_user = _user_whitelist(cfg)
    min_len = int(spell_cfg.get("min_len", 3))

    for m in TOKEN_RE.finditer(paragraph):
        tok = m.group(0)
        if len(tok) < min_len or _is_ignorable(tok) or tok.lower() in wl_user:
            continue

        ok = False
        suggestions = []
        if use_enchant and _ENCHANT_DICT is not None:
            try:
                ok = _ENCHANT_DICT.check(tok)
                if not ok:
                    suggestions = _ENCHANT_DICT.suggest(tok)[:3]
            except Exception:
                ok = False

        if not ok and _is_ok_by_wordlist(tok, cfg):
            ok = True

        if not ok:
            out.append(Issue(
                idx, m.start(), len(tok),
                SEVERITY_ERROR,
                CATEGORY["Орфография"],
                RID["SPELL_UNKNOWN"],
                f"Возможная орфографическая ошибка: «{tok}»",
                context_slice(paragraph, m.start()),
                suggestions
            ))
    return out
