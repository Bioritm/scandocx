# gost_precheck/core/regexes.py
import re

# --- пробелы/механика ---
RE_DOUBLE_SPACES = re.compile(r" {2,}")
RE_TABS          = re.compile(r"\t")
RE_TRAILING      = re.compile(r"[ \t]+$")

# --- скобочные пробелы ---
RE_PAREN_SPACE_AFTER_OPEN  = re.compile(r"\(\s")
RE_PAREN_SPACE_BEFORE_CLOSE= re.compile(r"\s\)")

# --- пунктуация ---
# лишний пробел ПЕРЕД знаком
RE_SPACE_BEFORE_PUNCT = re.compile(r" (?=[,.;:!?])")

# нет пробела ПОСЛЕ знака (исключаем случаи вроде ",)" или ",…")
RE_NO_SPACE_AFTER_PUNCT = re.compile(
    r"([,;:!?])(?![\s\)\]\}\-–—…]|$)"
)

# дубли знаков
RE_DOUBLE_COMMA  = re.compile(r",,")
RE_DOUBLE_SEMI   = re.compile(r";;")
RE_DOUBLE_COLON  = re.compile(r"::")
RE_TWO_DOTS      = re.compile(r"(?<!\.)\.\.(?!\.)")  # ровно две
RE_MANY_DOTS     = re.compile(r"\.{4,}")             # 4+

# минус вместо тире «между словами с пробелами»
RE_HYPHEN_AS_DASH = re.compile(r"(?<=\S) - (?=\S)")

# --- слово+цифра (Процедура1) ---
RE_WORD_DIGIT = re.compile(r"(?<![\d\W])[A-Za-zА-Яа-яЁё]+(?:-\w+)?\d+")


# gost_precheck/core/regexes.py
import re


# Подписи: "Таблица 1 — Название", "Рисунок 2 - Название", "Рис. 3 – Название"
RE_CAPTION = re.compile(
    r'^(?P<kind>Таблица|Рисунок|Рис\.)\s*(?P<num>\d+)\s*(?P<dash>[-–—])\s*(?P<title>.+)$',
    re.IGNORECASE
)

# Недопустимое тире (в подписи должно быть длинное '—')
RE_CAPTION_BAD_DASH = re.compile(
    r'^(?:Таблица|Рисунок|Рис\.)\s*\d+\s*([-–])\s*.+$',  # короткое или en-dash
    re.IGNORECASE
)

# Нет пробела до/после тире
RE_CAPTION_SPACING = re.compile(
    r'^(?:Таблица|Рисунок|Рис\.)\s*\d+(?:\s*[—]\S|\S[—]\s*)',  # нет пробела с одной стороны
    re.IGNORECASE
)

RE_DASH_WORDS = re.compile(r'(?<!\d)(?<=\S)\s-\s(?=\S)(?!\d)')
RE_DASH_TIGHT = re.compile(r'(?<!\d)(?<=\S)-(?!\d)(?=\S)')
RE_STRAIGHT_QUOTES = re.compile(r'"([^"\n]{1,200})"')