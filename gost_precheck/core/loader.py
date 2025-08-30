# gost_precheck/core/loader.py
import os
import re
import zipfile
from typing import List
from .utils import split_paragraphs_from_txt
from xml.etree.ElementTree import iterparse


# --- служебные нормализации -----------------------------------------------

_SPACE_MAP = {
    "\u00A0": " ",  # NBSP
    "\u202F": " ",  # NNBSP (узкий неразрывный)
    "\u2009": " ",  # THIN SPACE
}
_SPACE_TRANS = str.maketrans(_SPACE_MAP)

RE_MULTI_SPACE = re.compile(r"[ \t]{2,}")

# линия оглавления вида: «Название .......... 5»
RE_TOC_DOT_LEADER = re.compile(r"\.{3,}\s*\d+\s*$")

# «голые» номерные абзацы:  "1", "12", "3.4.5", "1.2. —" и т.п.
RE_JUST_NUMBERING = re.compile(r"^\s*\d+(?:\.\d+)*\s*[-–—]?\s*$")


# ---------------------------------------------------------------------------

def load_paragraphs(path: str) -> List[str]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return split_paragraphs_from_txt(f.read())
    elif ext == ".docx":
        return list(iter_docx_paragraphs(path))
    else:
        raise RuntimeError("Поддерживаются только .txt и .docx")


def _normalize(s: str) -> str:
    """NBSP/узкие пробелы → обычные; схлопнуть повторяющиеся пробелы."""
    s = s.translate(_SPACE_TRANS)
    s = RE_MULTI_SPACE.sub(" ", s)
    return s.strip()


def iter_docx_paragraphs(path: str):
    with zipfile.ZipFile(path) as z:
        with z.open("word/document.xml") as f:
            for event, elem in iterparse(f, events=("end",)):
                if elem.tag.endswith('}p'):
                    texts = []
                    for r in elem.iter():
                        if r.tag.endswith('}t'):
                            texts.append(r.text or "")

                    para = _normalize("".join(texts))

                    # фильтры-«шумодавы»: оглавление/пустяковые строки
                    if not para:
                        elem.clear()
                        continue
                    # «точечные лидеры» оглавления
                    if RE_TOC_DOT_LEADER.search(para) or (para.count('.') > len(para) * 0.40):
                        elem.clear()
                        continue
                    # «голая» нумерация разделов/номера страниц
                    if RE_JUST_NUMBERING.match(para):
                        elem.clear()
                        continue

                    yield para
                elem.clear()
