"""Build a docxtpl template from the sample Planner3 document."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "templates" / "Planner3_24August2026.docx"
DST = ROOT / "templates" / "lesson_plan_template.docx"
DEFAULTS = ROOT / "app" / "default_values.json"
FONT = "Jameel Noori Nastaleeq"
MAX_LIST = 8
MAX_ACT = 8


def set_para_text(paragraph, text: str, *, size_pt: float | None = None) -> None:
    """Replace text runs but keep any inline drawings (e.g. school logo)."""
    size = None
    for run in paragraph.runs:
        if run.font.size:
            size = run.font.size
            break

    p = paragraph._p
    for child in list(p):
        if child.tag != qn("w:r"):
            continue
        if child.find(qn("w:drawing")) is not None or child.find(qn("w:pict")) is not None:
            continue
        p.remove(child)

    run = paragraph.add_run(text)
    run.font.name = FONT
    if size_pt is not None:
        run.font.size = Pt(size_pt)
    elif size is not None:
        run.font.size = size


def set_cell_lines(cell, lines: list[str], *, size_pt: float | None = None) -> None:
    while len(cell.paragraphs) > 1:
        p = cell.paragraphs[-1]
        p._element.getparent().remove(p._element)
    if not lines:
        set_para_text(cell.paragraphs[0], "", size_pt=size_pt)
        return
    set_para_text(cell.paragraphs[0], lines[0], size_pt=size_pt)
    for line in lines[1:]:
        p = cell.add_paragraph()
        p.alignment = cell.paragraphs[0].alignment
        set_para_text(p, line, size_pt=size_pt)


def delete_row(table, row_idx: int) -> None:
    table._tbl.remove(table.rows[row_idx]._tr)


def ensure_data_rows(table, count: int) -> None:
    """Ensure table has 1 header + `count` data rows."""
    while len(table.rows) > count + 1:
        delete_row(table, len(table.rows) - 1)
    while len(table.rows) < count + 1:
        table._tbl.append(deepcopy(table.rows[-1]._tr))


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Missing source: {SRC}")

    shutil.copy2(SRC, DST)
    doc = Document(str(DST))

    outcomes = [
        "طلبہ نظم کے نئے الفاظ اور ان کے معانی سیکھیں گے۔",
        "طلبہ الفاظ کو استعمال کرتے ہوئے درست جملے بنائیں گے۔",
        "طلبہ نظم سے متعلق سوالات کے درست جوابات دے سکیں گے۔",
        "طلبہ نظم کے مرکزی خیال کو سمجھ سکیں گے۔",
    ]
    success_items = [
        "طلبہ کم از کم 10 الفاظ کے معانی درست بتائیں گے۔",
        "دیے گئے الفاظ سے درست جملے بنائیں گے۔",
        "تین سوالات کے درست جوابات لکھیں گے۔",
        "نظم کا مفہوم اپنے الفاظ میں بیان کریں گے۔",
    ]
    activities = [
        {
            "time": "10 منٹ",
            "materials": "درسی کتاب، وائٹ بورڈ",
            "assessment": "سوال و جواب",
            "student": "گزشتہ سبق کا اعادہ کریں اور نظم پڑھیں۔",
            "teacher": "سبق کا مختصر جائزہ اور SDG 4 کی اہمیت بیان کریں۔",
        },
        {
            "time": "20 منٹ",
            "materials": "درسی کتاب، چارٹ",
            "assessment": "زبانی سوالات",
            "student": "نئے الفاظ پڑھیں، معانی یاد کریں اور دہرائیں۔",
            "teacher": "الفاظ کے معانی مثالوں کے ساتھ سمجھائیں۔",
        },
        {
            "time": "20 منٹ",
            "materials": "کتاب، کاپی",
            "assessment": "انفرادی جائزہ",
            "student": "دیے گئے الفاظ سے جملے بنائیں۔",
            "teacher": "طلبہ کی رہنمائی کریں اور جملوں کی تصحیح کریں۔",
        },
        {
            "time": "20 منٹ",
            "materials": "درسی کتاب",
            "assessment": "تحریری جائزہ",
            "student": "نظم کے تین سوالات کے جوابات لکھیں۔",
            "teacher": "سوالات کی وضاحت کریں اور انفرادی مدد فراہم کریں۔",
        },
        {
            "time": "10 منٹ",
            "materials": "وائٹ بورڈ",
            "assessment": "زبانی فیڈبیک",
            "student": "سبق کا خلاصہ بیان کریں اور سوالات کے جواب دیں۔",
            "teacher": "سبق کا جائزہ لیں، فیڈبیک دیں اور گھر کے لیے دہرائی کی ہدایت کریں۔",
        },
    ]

    defaults = {
        "school_name": "دی لنکس اسکول",
        "plan_title": "سبق کا منصوبہ (جماعت سوم)",
        "subject_header": "سبق کا عنوان                             /موضوع",
        "lesson_title": "سبق کا عنوان: نظم: حمد (الفاظ/معانی، الفاظ سے جملے، سوال/جواب)",
        "sdg": "SDG: SDG 4 – معیاری تعلیم",
        "date": "۲۴ اگست",
        "date_label": "تاریخ",
        "class_value": "سوم",
        "class_label": "جماعت",
        "week": "دوسرا                 ہفتہ",
        "club_period": "کلب پیریڈ: 80 منٹ",
        "outcomes_label": "حاصلِ تعلم / کامیابی کے معیار",
        "objectives_label": "تعلیمی مقاصد",
        "col_time": "وقت",
        "col_materials": "تعلیمی مواد و وسائل",
        "col_assessment": "تشکیلِ جائزہ",
        "col_student": "طلبہ کی سرگرمی / طریقۂ تدریس",
        "col_teacher": "استاد کی سرگرمی",
        "review_heading": "سبق کا جائزہ",
        "review_body": (
            'طلبہ نے نظم "حمد" کے الفاظ اور معانی سیکھے، نئے الفاظ سے جملے بنائے، '
            "تین سوالات کے جوابات تحریر کیے اور نظم کے مرکزی خیال کو سمجھا۔ "
            "اس سبق کے ذریعے SDG 4 (معیاری تعلیم) کی اہمیت کو بھی اجاگر کیا گیا۔"
        ),
        "outcomes": outcomes,
        "success_items": success_items,
        "activities": activities,
    }
    for i in range(1, MAX_LIST + 1):
        defaults[f"outcome_{i}"] = outcomes[i - 1] if i <= len(outcomes) else ""
        defaults[f"success_{i}"] = success_items[i - 1] if i <= len(success_items) else ""
    for i in range(1, MAX_ACT + 1):
        if i <= len(activities):
            for key, value in activities[i - 1].items():
                defaults[f"a{i}_{key}"] = value
        else:
            for key in ("time", "materials", "assessment", "student", "teacher"):
                defaults[f"a{i}_{key}"] = ""

    set_para_text(doc.paragraphs[0], "{{school_name}}", size_pt=48)
    set_para_text(doc.paragraphs[1], "{{plan_title}}", size_pt=18)
    set_para_text(doc.paragraphs[5], "{{review_heading}}: ", size_pt=14)

    t0 = doc.tables[0]
    set_cell_lines(
        t0.rows[0].cells[0],
        ["{{subject_header}}", "{{lesson_title}}", "{{sdg}}"],
        size_pt=14,
    )
    set_cell_lines(t0.rows[0].cells[1], ["{{date}}"], size_pt=11)
    set_cell_lines(t0.rows[0].cells[2], ["{{date_label}}"], size_pt=14)
    set_cell_lines(t0.rows[0].cells[3], ["{{class_value}}"], size_pt=11)
    set_cell_lines(t0.rows[0].cells[4], ["{{class_label}}"], size_pt=14)
    set_cell_lines(t0.rows[0].cells[5], ["{{week}}"], size_pt=11)

    set_cell_lines(doc.tables[1].rows[0].cells[0], ["{{club_period}}"], size_pt=14)

    t2 = doc.tables[2]
    set_cell_lines(
        t2.rows[0].cells[0],
        [f"{{{{success_{i}}}}}" for i in range(1, MAX_LIST + 1)],
        size_pt=14,
    )
    set_cell_lines(t2.rows[0].cells[1], ["{{outcomes_label}}"], size_pt=14)
    set_cell_lines(
        t2.rows[0].cells[2],
        [f"{{{{outcome_{i}}}}}" for i in range(1, MAX_LIST + 1)],
        size_pt=14,
    )
    set_cell_lines(t2.rows[0].cells[3], ["{{objectives_label}}"], size_pt=14)

    t3 = doc.tables[3]
    set_cell_lines(t3.rows[0].cells[0], ["{{col_time}}"], size_pt=14)
    set_cell_lines(t3.rows[0].cells[1], ["{{col_materials}}"], size_pt=14)
    set_cell_lines(t3.rows[0].cells[2], ["{{col_assessment}}"], size_pt=14)
    set_cell_lines(t3.rows[0].cells[3], ["{{col_student}}"], size_pt=14)
    set_cell_lines(t3.rows[0].cells[4], ["{{col_teacher}}"], size_pt=14)

    ensure_data_rows(t3, MAX_ACT)
    for i in range(1, MAX_ACT + 1):
        cells = t3.rows[i].cells
        set_cell_lines(cells[0], [f"{{{{a{i}_time}}}}"], size_pt=11)
        set_cell_lines(cells[1], [f"{{{{a{i}_materials}}}}"], size_pt=11)
        set_cell_lines(cells[2], [f"{{{{a{i}_assessment}}}}"], size_pt=11)
        set_cell_lines(cells[3], [f"{{{{a{i}_student}}}}"], size_pt=11)
        set_cell_lines(cells[4], [f"{{{{a{i}_teacher}}}}"], size_pt=11)

    set_cell_lines(doc.tables[4].rows[0].cells[0], ["{{review_body}}"], size_pt=18)

    doc.save(str(DST))
    DEFAULTS.write_text(json.dumps(defaults, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {DST}")
    print(f"Wrote {DEFAULTS}")


if __name__ == "__main__":
    main()
