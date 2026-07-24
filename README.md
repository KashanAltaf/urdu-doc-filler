# Urdu Doc Filler — سبق کا منصوبہ

Edit every field of the Links School lesson-plan Word template in the browser, then download a filled `.docx` in **Jameel Noori Nastaleeq**.

## Run

```powershell
cd D:\urdu-doc-filler
.\run.bat
```

Or without a script:

```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000

If `.\run.ps1` fails with “running scripts is disabled”, use `run.bat` instead (or: `powershell -ExecutionPolicy Bypass -File .\run.ps1`).

## Files

| Path | Role |
|------|------|
| `templates/Planner3_24August2026.docx` | Your original sample |
| `templates/lesson_plan_template.docx` | Editable template (all `{{fields}}`) |
| `app/default_values.json` | Prefill values from the sample |
| `app/static/` | Urdu RTL form UI |

## Paste format

Paste a full lesson plan like this, then click **فارم میں بھریں** (or Generate — it auto-maps if needed):

```
سبق کا منصوبہ (جماعت سوم)

ہفتہ: دوسرا
سنگل پیریڈ: 40 منٹ
SDG: SDG 4 – معیاری تعلیم
سبق کا عنوان: …

تعلیمی مقاصد
…
حاصلِ تعلم / کامیابی کا معیار
…
وقت	مواد	…   (tab-separated rows)
سبق کا جائزہ
…
```

School name / date keep the template defaults unless you change them in the form.
