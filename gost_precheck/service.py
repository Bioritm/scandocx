# service.py
import uvicorn, tempfile, zipfile, os, io, json
from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from gost_precheck.core.config import load_all
from gost_precheck.core.engine import analyze_file
from gost_precheck.core.loader import load_paragraphs_from_ooxml  # добавим ниже

app = FastAPI(title="gost-precheck-local")

class AnalyzeRequest(BaseModel):
    ooxml: str                                    # полный OOXML документа из Word API
    settings_override: Optional[Dict[str, Any]] = None
    profile_path: Optional[str] = None            # путь к папке config_* (если нужно)

@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> Dict[str, Any]:
    # 1) грузим конфиг (профиль) и применяем overrides
    cfg = load_all(req.profile_path)
    if req.settings_override:
        cfg["settings"].update(req.settings_override)

    # 2) грузим абзацы из OOXML (без записи на диск)
    paragraphs, loader_stats, spans = load_paragraphs_from_ooxml(req.ooxml, cfg)

    # 3) анализ через текущее ядро (временно создадим .docx в temp для совместимости)
    #    — самый простой и стабильный путь на старте
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    tmp.close()
    # собираем минимальный docx с тем же document.xml
    with zipfile.ZipFile(tmp.name, "w") as z:
        # обязательные части упаковки .docx (content types + rels + document.xml)
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?>'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                   '</Types>')
        z.writestr("word/_rels/document.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                   '</Relationships>')
        z.writestr("word/document.xml", req.ooxml)

    issues, by_cat, debug_meta = analyze_file(tmp.name, cfg)
    os.unlink(tmp.name)

    # 4) вернём всё, плюс «map» для подсветки
    return {
        "issues_total": sum(by_cat.values()),
        "issues_by_category": by_cat,
        "issues": [i.to_dict() for i in issues],
        "debug": {**debug_meta, "loader_spans": spans},  # spans: координаты в тексте для клиентской подсветки
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
