from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.docx_fill import extract_placeholders, fill_template
from app.lesson_parse import (
    context_from_flat_fields,
    looks_like_lesson_paste,
    parse_lesson_paste,
)

ROOT = Path(__file__).resolve().parent.parent
UPLOADS = ROOT / "uploads"
OUTPUTS = ROOT / "outputs"
STATIC = ROOT / "app" / "static"
DEFAULT_TEMPLATE = ROOT / "templates" / "lesson_plan_template.docx"
DEFAULT_VALUES = ROOT / "app" / "default_values.json"

UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

app = FastAPI(title="Urdu Doc Filler")
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


class ParseBody(BaseModel):
    content: str = ""


def _load_defaults() -> dict:
    if DEFAULT_VALUES.exists():
        return json.loads(DEFAULT_VALUES.read_text(encoding="utf-8"))
    return {}


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/api/form")
async def form_config() -> dict:
    if not DEFAULT_TEMPLATE.exists():
        raise HTTPException(status_code=404, detail="پہلے سے طے شدہ ٹیمپلیٹ نہیں ملا۔")
    placeholders = extract_placeholders(DEFAULT_TEMPLATE.read_bytes())
    defaults = _load_defaults()
    return {
        "token": "default",
        "filename": DEFAULT_TEMPLATE.name,
        "placeholders": placeholders,
        "defaults": defaults,
    }


@app.post("/api/parse")
async def parse_content(body: ParseBody) -> dict:
    if not (body.content or "").strip():
        raise HTTPException(status_code=400, detail="مواد خالی ہے۔")
    parsed = parse_lesson_paste(body.content)
    return {"fields": parsed}


@app.post("/api/inspect")
async def inspect_template(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail="صرف .docx فائل اپ لوڈ کریں۔ پرانی .doc فائلوں کو پہلے Word میں .docx میں محفوظ کریں۔",
        )
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="فائل خالی ہے۔")
    placeholders = extract_placeholders(data)
    token = uuid.uuid4().hex
    (UPLOADS / f"{token}.docx").write_bytes(data)
    return {
        "token": token,
        "filename": file.filename,
        "placeholders": placeholders,
        "defaults": {},
    }


@app.post("/api/generate")
async def generate(
    token: str = Form(...),
    content: str = Form(""),
    fields_json: str = Form(""),
) -> FileResponse:
    if token == "default":
        template_path = DEFAULT_TEMPLATE
    else:
        template_path = UPLOADS / f"{token}.docx"

    if not template_path.exists():
        raise HTTPException(status_code=404, detail="ٹیمپلیٹ نہیں ملا۔ دوبارہ اپ لوڈ کریں۔")

    context: dict = dict(_load_defaults()) if token == "default" else {}

    if fields_json.strip():
        try:
            extra = json.loads(fields_json)
            if isinstance(extra, dict):
                for key, value in extra.items():
                    if isinstance(value, (list, dict)):
                        context[str(key)] = value
                    elif value is None:
                        context[str(key)] = ""
                    else:
                        context[str(key)] = str(value)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="فیلڈز کا ڈیٹا درست نہیں۔") from exc
    elif looks_like_lesson_paste(content):
        context.update(parse_lesson_paste(content))

    context = context_from_flat_fields(context)

    out_name = f"filled-{uuid.uuid4().hex[:8]}.docx"
    out_path = OUTPUTS / out_name
    fill_template(template_path.read_bytes(), context, out_path)

    return FileResponse(
        path=str(out_path),
        filename="بھرا_ہوا_دستاویز.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
