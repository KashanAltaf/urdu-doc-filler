from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.docx_fill import extract_placeholders, fill_template
from app.lesson_parse import (
    context_from_flat_fields,
    looks_like_lesson_paste,
    parse_lesson_paste,
)
from app.rag import build_index, chunk_text, extract_text, generate_fields, retrieve

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# On Vercel the filesystem is read-only except /tmp
if os.environ.get("VERCEL"):
    WORK = Path(tempfile.gettempdir()) / "urdu-doc-filler"
else:
    WORK = ROOT

UPLOADS = WORK / "uploads"
OUTPUTS = WORK / "outputs"
STATIC = ROOT / "app" / "static"
DEFAULT_TEMPLATE = ROOT / "templates" / "lesson_plan_template.docx"
DEFAULT_VALUES = ROOT / "app" / "default_values.json"

UPLOADS.mkdir(parents=True, exist_ok=True)
OUTPUTS.mkdir(parents=True, exist_ok=True)

LOCKED_HEADING_KEYS = (
    "subject_header",
    "date_label",
    "class_label",
    "outcomes_label",
    "objectives_label",
    "col_time",
    "col_teacher",
    "col_student",
    "col_assessment",
    "col_materials",
    "extra_rows_note",
    "review_heading",
)

app = FastAPI(title="Urdu Doc Filler")
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


class ParseBody(BaseModel):
    content: str = ""


def _load_defaults() -> dict:
    if DEFAULT_VALUES.exists():
        return json.loads(DEFAULT_VALUES.read_text(encoding="utf-8"))
    return {}


def _apply_locked_headings(context: dict, defaults: dict) -> dict:
    for key in LOCKED_HEADING_KEYS:
        if key in defaults:
            context[key] = defaults[key]
    return context


def _docx_response(path: Path) -> Response:
    data = path.read_bytes()
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
    filename = "بھرا_ہوا_دستاویز.docx"
    encoded = quote(filename)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
        },
    )

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
) -> Response:
    if token == "default":
        template_path = DEFAULT_TEMPLATE
    else:
        template_path = UPLOADS / f"{token}.docx"

    if not template_path.exists():
        raise HTTPException(status_code=404, detail="ٹیمپلیٹ نہیں ملا۔ دوبارہ اپ لوڈ کریں۔")

    context: dict = dict(_load_defaults()) if token == "default" else {}
    defaults = _load_defaults()

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

    context = _apply_locked_headings(context, defaults)
    context = context_from_flat_fields(context)

    out_name = f"filled-{uuid.uuid4().hex[:8]}.docx"
    out_path = OUTPUTS / out_name
    fill_template(template_path.read_bytes(), context, out_path)
    return _docx_response(out_path)


@app.post("/api/rag-generate")
async def rag_generate(
    prompt: str = Form(...),
    date: str = Form(""),
    book_text: str = Form(""),
    file: UploadFile | None = File(None),
) -> Response:
    """
    Build a lesson plan from book text + prompt.

    Prefer `book_text` (extracted in the browser) so Vercel stays under
    the ~4.5MB request body limit. Optional `file` still works locally.
    """
    if not DEFAULT_TEMPLATE.exists():
        raise HTTPException(status_code=404, detail="پہلے سے طے شدہ ٹیمپلیٹ نہیں ملا۔")

    prompt = (prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="پرامپٹ خالی ہے۔")

    date = (date or "").strip()
    if date:
        prompt = f"{prompt}\n\nتاریخ: {date}"

    text = (book_text or "").strip()
    if not text and file is not None and file.filename:
        filename = file.filename or ""
        lower = filename.lower()
        if not (lower.endswith(".pdf") or lower.endswith(".docx")):
            raise HTTPException(status_code=400, detail="صرف PDF یا DOCX فائلیں قبول ہیں۔")
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="فائل خالی ہے۔")
        if len(data) > 4 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="فائل بہت بڑی ہے۔ براؤزر میں متن نکال کر بھیجیں، یا چھوٹی فائل استعمال کریں۔",
            )
        try:
            text = extract_text(filename, data)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not text:
        raise HTTPException(
            status_code=400,
            detail="کتاب کا متن نہیں ملا۔ PDF/DOCX اپ لوڈ کریں۔",
        )

    # Keep payload/RAG practical on free tiers
    if len(text) > 180_000:
        text = text[:180_000]

    try:
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("کتاب سے متن نہیں نکلا۔ اسکین شدہ PDF ہو تو پہلے OCR کریں۔")
        if len(chunks) > 80:
            chunks = chunks[:80]
        index = build_index(chunks)
        hits = retrieve(index, prompt, top_k=6)
        fields = generate_fields(user_prompt=prompt, retrieved_chunks=hits)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"RAG ناکام: {exc}",
        ) from exc

    defaults = _load_defaults()
    context: dict = dict(defaults)
    context.update(fields)
    if date:
        context["date"] = date
    context = _apply_locked_headings(context, defaults)
    context = context_from_flat_fields(context)

    out_name = f"rag-{uuid.uuid4().hex[:8]}.docx"
    out_path = OUTPUTS / out_name
    fill_template(DEFAULT_TEMPLATE.read_bytes(), context, out_path)
    return _docx_response(out_path)
