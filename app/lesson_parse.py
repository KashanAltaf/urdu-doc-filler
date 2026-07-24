"""Parse pasted Urdu lesson-plan text into template fields."""

from __future__ import annotations

import re
from typing import Any

CLASS_IN_TITLE = re.compile(r"جماعت\s+([^)\n]+)")
KV_LINE = re.compile(r"^([^:\n]+)\s*[:：]\s*(.+)$")


def _norm(s: str) -> str:
    return (s or "").replace("\u200c", "").replace("\ufeff", "").strip()


def _is_objectives_header(line: str) -> bool:
    t = _norm(line)
    return t == "تعلیمی مقاصد" or t.startswith("تعلیمی مقاصد")


def _is_success_header(line: str) -> bool:
    t = _norm(line)
    return "حاصل" in t and ("تعلم" in t or "تعلّم" in t or "معیار" in t)


def _is_review_header(line: str) -> bool:
    t = _norm(line).rstrip(":：")
    return t == "سبق کا جائزہ" or t.startswith("سبق کا جائزہ")


def _is_table_header(line: str) -> bool:
    t = _norm(line)
    return "وقت" in t and ("مواد" in t or "وسائل" in t)


def _split_row(line: str) -> list[str]:
    if "\t" in line:
        parts = [p.strip() for p in line.split("\t")]
    else:
        parts = [p.strip() for p in re.split(r"\s{2,}", line)]
    return [p for p in parts if p]


def parse_lesson_paste(text: str) -> dict[str, Any]:
    """
    Map free-form pasted lesson plan text to document fields.

    Expected shape (flexible):
      سبق کا منصوبہ (جماعت …)
      ہفتہ: …
      سنگل/کلب پیریڈ: …
      SDG: …
      سبق کا عنوان: …
      تعلیمی مقاصد
      …
      حاصلِ تعلم / کامیابی کا معیار
      …
      <table header + rows>
      سبق کا جائزہ
      …
    """
    raw_lines = (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = [_norm(x) for x in raw_lines]

    result: dict[str, Any] = {
        "outcomes": [],
        "success_items": [],
        "activities": [],
    }

    mode: str | None = None
    review_parts: list[str] = []

    for line in lines:
        if not line:
            if mode == "review" and review_parts:
                # keep paragraph breaks as spaces already handled by join
                continue
            continue

        if _is_objectives_header(line):
            mode = "objectives"
            result["objectives_label"] = "تعلیمی مقاصد"
            continue
        if _is_success_header(line):
            mode = "success"
            result["outcomes_label"] = line
            continue
        if _is_table_header(line):
            mode = "table"
            cols = _split_row(line)
            if len(cols) >= 5:
                result["col_time"] = cols[0]
                result["col_materials"] = cols[1]
                result["col_assessment"] = cols[2]
                result["col_student"] = cols[3]
                result["col_teacher"] = cols[4]
            continue
        if _is_review_header(line):
            mode = "review"
            result["review_heading"] = line.rstrip(":：").strip()
            continue

        if mode == "objectives":
            result["outcomes"].append(line)
            continue
        if mode == "success":
            result["success_items"].append(line)
            continue
        if mode == "table":
            cols = _split_row(line)
            if len(cols) >= 5:
                result["activities"].append(
                    {
                        "time": cols[0],
                        "materials": cols[1],
                        "assessment": cols[2],
                        "student": cols[3],
                        "teacher": cols[4],
                    }
                )
            continue
        if mode == "review":
            review_parts.append(line)
            continue

        # Top matter / key-value before sections
        if line.startswith("سبق کا منصوبہ"):
            result["plan_title"] = line
            m = CLASS_IN_TITLE.search(line)
            if m:
                result["class_value"] = m.group(1).strip()
            continue

        kv = KV_LINE.match(line)
        if not kv:
            continue
        key, value = _norm(kv.group(1)), _norm(kv.group(2))
        key_compact = key.replace(" ", "")

        if key == "ہفتہ" or key.startswith("ہفتہ"):
            result["week"] = value if "ہفتہ" in value else f"{value} ہفتہ"
        elif "پیریڈ" in key or "پیرڈ" in key:
            result["club_period"] = line  # keep full "سنگل پیریڈ: 40 منٹ"
        elif key.upper().startswith("SDG") or key == "SDG":
            result["sdg"] = line if line.upper().startswith("SDG") else f"SDG: {value}"
        elif "عنوان" in key:
            result["lesson_title"] = line if "سبق" in key else f"سبق کا عنوان: {value}"
        elif key == "تاریخ":
            result["date"] = value
        elif key == "جماعت":
            result["class_value"] = value
        elif "اسکول" in key or key_compact == "اسکولکانام":
            result["school_name"] = value

    if review_parts:
        result["review_body"] = " ".join(review_parts)

    return flatten_for_form(result)


def flatten_for_form(parsed: dict[str, Any]) -> dict[str, Any]:
    """Add outcome_1.. / a1_time.. keys for the editable form."""
    out = dict(parsed)
    outcomes = list(parsed.get("outcomes") or [])
    success = list(parsed.get("success_items") or [])
    activities = list(parsed.get("activities") or [])

    for i in range(1, 9):
        out[f"outcome_{i}"] = outcomes[i - 1] if i <= len(outcomes) else ""
        out[f"success_{i}"] = success[i - 1] if i <= len(success) else ""

    for i in range(1, 9):
        if i <= len(activities):
            row = activities[i - 1]
            out[f"a{i}_time"] = row.get("time", "")
            out[f"a{i}_materials"] = row.get("materials", "")
            out[f"a{i}_assessment"] = row.get("assessment", "")
            out[f"a{i}_student"] = row.get("student", "")
            out[f"a{i}_teacher"] = row.get("teacher", "")
        else:
            for part in ("time", "materials", "assessment", "student", "teacher"):
                out[f"a{i}_{part}"] = ""

    out["outcomes"] = outcomes
    out["success_items"] = success
    out["activities"] = activities
    return out


def context_from_flat_fields(fields: dict[str, Any]) -> dict[str, Any]:
    """Rebuild list context from flat form fields for the Word template."""
    ctx = dict(fields)

    outcomes = []
    for i in range(1, 9):
        val = str(fields.get(f"outcome_{i}", "") or "").strip()
        if val:
            outcomes.append(val)
    if not outcomes and fields.get("outcomes"):
        outcomes = [str(x).strip() for x in fields["outcomes"] if str(x).strip()]

    success = []
    for i in range(1, 9):
        val = str(fields.get(f"success_{i}", "") or "").strip()
        if val:
            success.append(val)
    if not success and fields.get("success_items"):
        success = [str(x).strip() for x in fields["success_items"] if str(x).strip()]

    activities = []
    for i in range(1, 9):
        row = {
            "time": str(fields.get(f"a{i}_time", "") or "").strip(),
            "materials": str(fields.get(f"a{i}_materials", "") or "").strip(),
            "assessment": str(fields.get(f"a{i}_assessment", "") or "").strip(),
            "student": str(fields.get(f"a{i}_student", "") or "").strip(),
            "teacher": str(fields.get(f"a{i}_teacher", "") or "").strip(),
        }
        if any(row.values()):
            activities.append(row)
    if not activities and fields.get("activities"):
        activities = fields["activities"]

    ctx["outcomes"] = outcomes
    ctx["success_items"] = success
    ctx["activities"] = activities
    return ctx


def looks_like_lesson_paste(text: str) -> bool:
    t = text or ""
    return ("تعلیمی مقاصد" in t) or ("سبق کا منصوبہ" in t) or ("سبق کا جائزہ" in t)
