# Urdu Doc Filler — سبق کا منصوبہ (RAG)

Upload a **PDF/DOCX textbook** + write a **prompt**. The app retrieves relevant passages (RAG), asks **Google Gemini** (free tier) to fill the lesson-plan fields, and downloads a `.docx` in **Jameel Noori Nastaleeq**.

## Free API key (Gemini)

1. Open [Google AI Studio → API key](https://aistudio.google.com/apikey)
2. Create a key (free)
3. In the project folder, copy `.env.example` → `.env` and set:

```
GEMINI_API_KEY=your_key_here
```

On **Vercel**: Project → Settings → Environment Variables → add `GEMINI_API_KEY`.

## Run locally

```powershell
cd D:\urdu-doc-filler
.\.venv\Scripts\pip.exe install -r requirements.txt
.\run.bat
```

Open http://127.0.0.1:8000

1. Upload a book (PDF or DOCX)
2. Write a prompt (e.g. class, lesson title, week)
3. Download the filled lesson plan

## Deploy to Vercel

1. Push the repo (include `templates/lesson_plan_template.docx`)
2. Import on [vercel.com/new](https://vercel.com/new)
3. Add env var `GEMINI_API_KEY`
4. Deploy

`vercel.json` sets `maxDuration` to 120s (RAG + Word fill).

## How it works

1. Extract text from PDF/DOCX → chunk
2. Embed chunks with Gemini `text-embedding-004`
3. Retrieve top passages for your prompt
4. `gemini-2.0-flash` returns lesson-plan JSON
5. Locked form headings stay from `default_values.json`
6. Fill `templates/lesson_plan_template.docx` → download

## Project files

| Path | Role |
|------|------|
| `app/main.py` | FastAPI (`/api/rag-generate`) |
| `app/rag/` | Extract, embed/retrieve, Gemini generate |
| `templates/lesson_plan_template.docx` | Fillable Word template |
| `app/default_values.json` | Locked headings + defaults |
| `.env.example` | Gemini key template |
| `vercel.json` | Vercel function settings |
