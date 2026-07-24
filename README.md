# Urdu Doc Filler — سبق کا منصوبہ

Paste an Urdu lesson plan, map it onto the Word template, download a filled `.docx` in **Jameel Noori Nastaleeq**.

## Run locally

```powershell
cd D:\urdu-doc-filler
.\run.bat
```

Open http://127.0.0.1:8000

Or:

```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

## Deploy to Vercel (step by step)

### 1. Commit and push these files to GitHub

Make sure your GitHub repo includes at least:

- `app/` (all Python + `static/` + `default_values.json`)
- `templates/lesson_plan_template.docx` (required)
- `requirements.txt`
- `vercel.json`

From the project folder:

```powershell
cd D:\urdu-doc-filler
git add app templates/lesson_plan_template.docx requirements.txt vercel.json README.md
git status
git commit -m "Add Vercel deployment config"
git push
```

If `lesson_plan_template.docx` is missing from git, the live site cannot generate documents.

### 2. Open Vercel and import the repo

1. Go to [https://vercel.com/new](https://vercel.com/new)
2. Sign in with GitHub if needed
3. Click **Import** next to your `urdu-doc-filler` (or whatever you named it) repository
4. Framework Preset: leave as **Other** / auto-detected **FastAPI** if shown
5. Root Directory: `./` (repo root)
6. Build Command: leave empty (Vercel handles FastAPI)
7. Output Directory: leave empty
8. Click **Deploy**

### 3. Wait for the build

- Vercel installs `requirements.txt` and deploys `app/main.py` as a FastAPI function
- When it finishes, open the `.vercel.app` URL it gives you

### 4. Test the live site

1. Open the Vercel URL
2. Paste a lesson plan
3. Click **دستاویز بنائیں اور ڈاؤن لوڈ کریں**
4. Confirm the `.docx` downloads

### 5. Optional: custom domain

In the Vercel project → **Settings → Domains** → add your domain.

### Notes

- `vercel.json` sets `maxDuration` to 60 seconds (Word generation needs time)
- On Vercel, temp files use `/tmp` automatically (`VERCEL` env)
- Hobby plan works; if generate times out, upgrade or raise `maxDuration` (Pro)

### Redeploy after changes

```powershell
git add .
git commit -m "Update app"
git push
```

Vercel redeploys from GitHub automatically.

## Paste format

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

## Project files

| Path | Role |
|------|------|
| `app/main.py` | FastAPI app (Vercel entrypoint) |
| `templates/lesson formet in urdu 2026.docx` | Source form (layout/format) |
| `templates/lesson_plan_template.docx` | Fillable template used for downloads |
| `app/default_values.json` | Default field values |
| `vercel.json` | Vercel function settings |
| `requirements.txt` | Python dependencies |
