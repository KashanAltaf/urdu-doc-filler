Set-Location $PSScriptRoot
& .\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
