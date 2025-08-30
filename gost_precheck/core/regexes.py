# -*- coding: utf-8 -*-
import re

# Любой «пробельный» символ, который часто встречается в .docx:
# обычный пробел + NBSP + узкие пробелы.
SP = r"[ \u00A0\u202F\u2009]"

# --- whitespace -------------------------------------------------------------

RE_TABS = re.compile(r"\t")
RE_TRAILING = re.compile(rf"{SP}+$")
RE_DOUBLE_SPACES = re.compile(rf"{SP}{{2,}}")

# Скобки «( xxx» и «xxx )»
RE_PAREN_SPACE_AFTER_OPEN = re.compile(r"\(\s")
RE_PAREN_SPACE_BEFORE_CLOSE = re.compile(r"\s\)")

# --- punctuation ------------------------------------------------------------

# Лишний пробел ПЕРЕД знаком препинания (закрывающие знаки)
RE_SPACE_BEFORE_PUNCT = re.compile(rf"{SP}+(?=[,;:.!?%)»])")

# Нет пробела ПОСЛЕ знака препинания.
# 1) запятая — исключаем числа формата 1,23
# 2) прочие знаки — просто требуем пробел после
RE_NO_SPACE_AFTER_PUNCT = re.compile(
    rf"(?:(?<!\d),(?![\s\d])|;(?!{SP})|:(?!{SP})|[!?](?!{SP}))"
)

# Повторы знаков
RE_DOUBLE_COMMA = re.compile(r",\s*,")
RE_DOUBLE_SEMI = re.compile(r";\s*;")
RE_DOUBLE_COLON = re.compile(r":\s*:")

# ".." (но не часть "..." или "....")
RE_TWO_DOTS = re.compile(r"(?<!\.)\.\.(?!\.)")

# 4+ точек
RE_MANY_DOTS = re.compile(r"\.{4,}")

# Нет пробела между словом и числом: "Глава5", "версия15"
RE_WORD_DIGIT = re.compile(r"([A-Za-zА-Яа-яЁё])([0-9])")

# Нет пробела между числом и словом: "5глава", "15версия"
RE_DIGIT_WORD = re.compile(r"([0-9])([A-Za-zА-Яа-яЁё])")