# gost_precheck/core/regexes.py
import re

NBSP = "\u00A0"

# --- базовые токены ---
RE_WORD_TOKEN = re.compile(r"[A-Za-zА-Яа-яЁё\-]{2,}")
RE_RU_WORD    = re.compile(r"[А-Яа-яЁё\-]{2,}")
RE_LAT_WORD   = re.compile(r"[A-Za-z\-]{2,}")

# --- пробелы/механика ---
RE_DOUBLE_SPACES = re.compile(r"(?<=\S) {2,}(?=\S)")
RE_TABS          = re.compile(r"\t+")
RE_LEADING_TABS  = re.compile(r"^\t+")
RE_TRAILING      = re.compile(r"[ \t]+$")

# --- скобочные пробелы ---
RE_PAREN_SPACE_AFTER_OPEN   = re.compile(r"\(\s")
RE_PAREN_SPACE_BEFORE_CLOSE = re.compile(r"\s\)")

# --- пунктуация ---
RE_SPACE_BEFORE_PUNCT    = re.compile(r"(?<=\S)\s+(?=[,;:.!?])")
RE_NO_SPACE_AFTER_PUNCT  = re.compile(r"([,;:])(?!\s|$)")
RE_DOUBLE_COMMA          = re.compile(r",,")
RE_DOUBLE_SEMI           = re.compile(r";;")
RE_DOUBLE_COLON          = re.compile(r"::")
RE_TWO_DOTS              = re.compile(r"(?<!\.)\.\.(?!\.)")  # ровно две
RE_MANY_DOTS             = re.compile(r"\.{4,}")             # 4+

# дефис вместо тире (между словами; не трогаем минусы/диапазоны в числах)
RE_HYPHEN_AS_DASH        = re.compile(r"(?<!\d)(?<=\S)\s-\s(?=\S)(?!\d)")

# прямые кавычки "..." (короткие сегменты, чтобы не трогать URL/код)
RE_STRAIGHT_QUOTES       = re.compile(r'"([^"\n]{1,200})"')

# стык кириллица↔латиница без пробела: далееPostgres / APIдокумент
RE_CYR_LAT_NO_SPACE      = re.compile(r"(?i)(?<=[А-ЯЁа-яё])(?=[A-Z])|(?<=[A-Z])(?=[А-ЯЁа-яё])")

# --- слово+цифра, «Процедура1», «п.3.1Схема» и т.п. ---
RE_WORD_DIGIT            = re.compile(r"(?<![\d\W])[A-Za-zА-Яа-яЁё]+(?:-\w+)?\d+")

# --- подписи ---
# "Таблица 1 — Название", "Рисунок 2 - Название", "Рис. 3 – Название"
RE_CAPTION = re.compile(
    r'^(?P<kind>(Таблица|Табл\.|Рисунок|Рис\.))\s+'
    r'(?P<num>\d+(?:\.\d+)*)\s*'
    r'(?P<dash>[—–-])\s*'
    r'(?P<title>.*)$',
    re.IGNORECASE
)

# «плохое» тире в подписи (должно быть именно эм-даш —)
RE_CAPTION_BAD_DASH = re.compile(
    r'^(?:Таблица|Табл\.|Рисунок|Рис\.)\s*\d+(?:\.\d+)*\s*([-–])\s*.+$',
    re.IGNORECASE
)

# нет пробела слева/справа от тире в подписи
RE_CAPTION_SPACING = re.compile(
    r'^(?:Таблица|Табл\.|Рисунок|Рис\.)\s*\d+(?:\.\d+)*'
    r'(?:\s*[—]\S|\S[—]\s*)',
    re.IGNORECASE
)
