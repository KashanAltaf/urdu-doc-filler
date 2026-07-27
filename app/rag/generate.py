"""Generate lesson-plan field JSON with Gemini (free tier) from RAG context."""

from __future__ import annotations

import json
import os
import re
from typing import Any


FIELD_SCHEMA_HINT = """
Return ONE JSON object. All values must be strings (or arrays of strings where noted).
Use Urdu. Empty string if unknown. Do not invent form column headings.

String keys:
- lesson_title (e.g. "سبق کا عنوان: …")
- date
- class_value (e.g. "سوم")
- week (e.g. "دوسرا ہفتہ")
- club_period (e.g. "سنگل پیریڈ: 40 منٹ")
- sdg (e.g. "SDG: SDG 4 – معیاری تعلیم")
- review_body (سبق کا جائزہ کا متن)
- a1_time, a1_teacher, a1_student, a1_assessment, a1_materials
- a2_time, a2_teacher, a2_student, a2_assessment, a2_materials
- a3_time, a3_teacher, a3_student, a3_assessment, a3_materials
(optional a4_*, a5_* same pattern)

Array keys (list of Urdu bullet lines):
- outcomes  (تعلیمی مقاصد — 3 to 6 items)
- success_items  (حاصلِ تعلم / کامیابی کے معیار — 3 to 6 items)

You may instead use flat keys outcome_1..outcome_8 and success_1..success_8.
""".strip()


SYSTEM = """آپ ایک ماہر اردو سبق پلانر ہیں۔
دی گئی کتاب کے اقتباسات اور صارف کے پرامپٹ سے ایک مکمل سبق کا منصوبہ بنائیں۔
صرف درست JSON آبجیکٹ واپس کریں — کوئی markdown، کوئی وضاحت نہیں۔
مواد اردو میں لکھیں، واضح اور عملی ہو۔
سرگرمیاں تین حصوں میں تقسیم کریں (ابتدائیہ / ترقیہ / اختتامیہ یا مناسب تقسیم)۔
وقت منٹ میں لکھیں جہاں ممکن ہو۔
""".strip()


def _client():
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY سیٹ نہیں ہے۔ Google AI Studio سے مفت کلید لیں: https://aistudio.google.com/apikey"
        )
    return genai.Client(api_key=api_key)


def _parse_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("ماڈل نے خالی جواب دیا۔")
    # strip ```json fences if present
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(text[start : end + 1])
        else:
            raise ValueError("ماڈل کا جواب JSON نہیں تھا۔") from None
    if not isinstance(data, dict):
        raise ValueError("JSON آبجیکٹ درکار ہے۔")
    # stringify / keep list fields for outcomes & activities
    out: dict[str, Any] = {}
    for k, v in data.items():
        key = str(k)
        if v is None:
            out[key] = ""
        elif key in ("outcomes", "success_items", "activities") and isinstance(v, list):
            out[key] = v
        elif isinstance(v, (list, dict)):
            out[key] = json.dumps(v, ensure_ascii=False)
        else:
            out[key] = str(v).strip()
    return out


def generate_fields(
    *,
    user_prompt: str,
    retrieved_chunks: list[str],
    model: str | None = None,
) -> dict[str, Any]:
    client = _client()
    model_name = model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    context = "\n\n---\n\n".join(retrieved_chunks) if retrieved_chunks else "(کوئی حوالہ نہیں)"
    user = f"""صارف کا پرامپٹ:
{user_prompt.strip()}

کتاب سے متعلقہ اقتباسات:
{context}

{FIELD_SCHEMA_HINT}
"""

    from google.genai import types

    response = client.models.generate_content(
        model=model_name,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            temperature=0.4,
            response_mime_type="application/json",
        ),
    )
    text = getattr(response, "text", None) or ""
    if not text and getattr(response, "candidates", None):
        # fallback gather
        parts = []
        for c in response.candidates:
            content = getattr(c, "content", None)
            if not content:
                continue
            for p in getattr(content, "parts", []) or []:
                t = getattr(p, "text", None)
                if t:
                    parts.append(t)
        text = "\n".join(parts)
    return _parse_json(text)
