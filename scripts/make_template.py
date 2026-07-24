"""Build lesson_plan_template.docx from the 2026 Urdu lesson form.

Preserves alignment/font sizes from the source. Paste field names stay the
same; only Word cell placement follows the new form layout.
"""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "templates" / "lesson formet in urdu 2026.docx"
DST = ROOT / "templates" / "lesson_plan_template.docx"
DEFAULTS = ROOT / "app" / "default_values.json"
FONT = "Jameel Noori Nastaleeq"
MAX_LIST = 8
MAX_ACT = 5  # blank data rows under the prompt row


def _format_from_paragraph(paragraph):
    candidates = []
    for run in paragraph.runs:
        el = run._element
        if el.find(qn("w:drawing")) is not None and not (run.text or "").strip():
            continue
        candidates.append(run)

    for run in candidates:
        if (run.text or "").strip():
            rPr = run._element.find(qn("w:rPr"))
            return (deepcopy(rPr) if rPr is not None else None), run.font.size

    for run in candidates:
        rPr = run._element.find(qn("w:rPr"))
        if rPr is not None:
            return deepcopy(rPr), run.font.size

    pPr = paragraph._p.find(qn("w:pPr"))
    if pPr is not None:
        rPr = pPr.find(qn("w:rPr"))
        if rPr is not None:
            return deepcopy(rPr), None
    return None, None


def set_para_text(paragraph, text: str) -> None:
    rPr_clone, size = _format_from_paragraph(paragraph)
    p = paragraph._p
    for child in list(p):
        if child.tag != qn("w:r"):
            continue
        if child.find(qn("w:drawing")) is not None or child.find(qn("w:pict")) is not None:
            continue
        p.remove(child)

    run = paragraph.add_run(text)
    if rPr_clone is not None:
        existing = run._element.find(qn("w:rPr"))
        if existing is not None:
            run._element.remove(existing)
        run._element.insert(0, rPr_clone)
    else:
        run.font.name = FONT
        if size is not None:
            run.font.size = size


def set_cell_lines(cell, lines: list[str]) -> None:
    if not cell.paragraphs:
        return

    while len(cell.paragraphs) > 1:
        p = cell.paragraphs[-1]
        p._element.getparent().remove(p._element)

    first = cell.paragraphs[0]
    if not lines:
        set_para_text(first, "")
        return

    set_para_text(first, lines[0])
    anchor = first._p
    for _ in lines[1:]:
        clone = deepcopy(anchor)
        anchor.addnext(clone)
        anchor = clone

    paras = cell.paragraphs
    for i, line in enumerate(lines):
        set_para_text(paras[i], line)


def delete_row(table, row_idx: int) -> None:
    table._tbl.remove(table.rows[row_idx]._tr)


def ensure_activity_data_rows(table, count: int) -> None:
    """Keep header row 0; ensure `count` blank data rows from index 1."""
    target = 1 + count
    while len(table.rows) > target:
        delete_row(table, len(table.rows) - 1)
    while len(table.rows) < target:
        table._tbl.append(deepcopy(table.rows[-1]._tr))


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Missing source: {SRC}")

    shutil.copy2(SRC, DST)
    doc = Document(str(DST))

    defaults = {
        "school_name": "دی لنکس اسکول",
        "plan_title": "سبق کا منصوبہ",
        "subject_header": "سبق کا عنوان / موضوع",
        "lesson_title": "",
        "sdg": "",
        "date": "",
        "date_label": "تاریخ",
        "class_value": "",
        "class_label": "جماعت",
        "week": "",
        "club_period": "دورانیہ",
        "outcomes_label": "حاصلِ تعلم / کامیابی کے معیار",
        "objectives_label": "تعلیمی مقاصد",
        "col_time": "وقت",
        "col_teacher": "موضوع کا مواد اور استاد کی سرگرمی",
        "col_student": "طلبہ کی سرگرمی / طریقۂ تدریس",
        "col_assessment": "تشکیلی جائزہ",
        "col_materials": "تعلیمی مواد اور وسائل",
        "review_heading": "سبق کا جائزہ",
        "review_body": "",
        "outcomes": [],
        "success_items": [],
        "activities": [],
        "extra_rows_note": "ضرورت کے مطابق مزید قطاریں شامل کریں۔",
    }
    for i in range(1, MAX_LIST + 1):
        defaults[f"outcome_{i}"] = ""
        defaults[f"success_{i}"] = ""
    for i in range(1, MAX_ACT + 1):
        for key in ("time", "materials", "assessment", "student", "teacher"):
            defaults[f"a{i}_{key}"] = ""

    # Body paragraphs — keep P5 instructional note as-is
    set_para_text(doc.paragraphs[0], "{{school_name}}")
    set_para_text(doc.paragraphs[1], "{{plan_title}}")
    set_para_text(doc.paragraphs[5], "{{extra_rows_note}}")
    set_para_text(doc.paragraphs[6], "{{review_heading}}: ")

    # Table 0 — match filled Planner layout (wide title cell + date/class/week)
    # C0 title block | C1 date | C2 تاریخ | C3 class | C4 جماعت | C5 week
    t0 = doc.tables[0]
    set_cell_lines(
        t0.rows[0].cells[0],
        ["{{subject_header}}", "{{lesson_title}}", "{{sdg}}"],
    )
    set_cell_lines(t0.rows[0].cells[1], ["{{date}}"])
    set_cell_lines(t0.rows[0].cells[2], ["{{date_label}}"])
    set_cell_lines(t0.rows[0].cells[3], ["{{class_value}}"])
    set_cell_lines(t0.rows[0].cells[4], ["{{class_label}}"])
    set_cell_lines(t0.rows[0].cells[5], ["{{week}}"])

    # Table 1 — duration
    set_cell_lines(doc.tables[1].rows[0].cells[0], ["{{club_period}}"])

    # Table 2 — success (C0) | label | objectives (C2) | label
    t2 = doc.tables[2]
    set_cell_lines(
        t2.rows[0].cells[0],
        [f"{{{{success_{i}}}}}" for i in range(1, MAX_LIST + 1)],
    )
    set_cell_lines(t2.rows[0].cells[1], ["{{outcomes_label}}"])
    set_cell_lines(
        t2.rows[0].cells[2],
        [f"{{{{outcome_{i}}}}}" for i in range(1, MAX_LIST + 1)],
    )
    set_cell_lines(t2.rows[0].cells[3], ["{{objectives_label}}"])

    # Table 3 — activity grid (new column order)
    t3 = doc.tables[3]
    set_cell_lines(t3.rows[0].cells[0], ["{{col_time}}"])
    set_cell_lines(t3.rows[0].cells[1], ["{{col_teacher}}"])
    set_cell_lines(t3.rows[0].cells[2], ["{{col_student}}"])
    set_cell_lines(t3.rows[0].cells[3], ["{{col_assessment}}"])
    set_cell_lines(t3.rows[0].cells[4], ["{{col_materials}}"])

    # Remove instructional prompt row (old row 1) if present
    if len(t3.rows) > 1:
        prompt_text = t3.rows[1].cells[1].text if len(t3.rows[1].cells) > 1 else ""
        if "کیسے سمجھائیں" in prompt_text or "سیکھنے کی پیش رفت" in prompt_text:
            delete_row(t3, 1)

    ensure_activity_data_rows(t3, MAX_ACT)
    for i in range(1, MAX_ACT + 1):
        row = t3.rows[i]  # row 0 = header; data starts at 1
        # New form: time | teacher | student | assessment | materials
        set_cell_lines(row.cells[0], [f"{{{{a{i}_time}}}}"])
        set_cell_lines(row.cells[1], [f"{{{{a{i}_teacher}}}}"])
        set_cell_lines(row.cells[2], [f"{{{{a{i}_student}}}}"])
        set_cell_lines(row.cells[3], [f"{{{{a{i}_assessment}}}}"])
        set_cell_lines(row.cells[4], [f"{{{{a{i}_materials}}}}"])

    # Table 4 — review body
    set_cell_lines(doc.tables[4].rows[0].cells[0], ["{{review_body}}"])

    doc.save(str(DST))
    DEFAULTS.write_text(json.dumps(defaults, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {DST}")
    print(f"Wrote {DEFAULTS}")
    print(f"Source: {SRC.name}")


if __name__ == "__main__":
    main()
