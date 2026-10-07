# AI CV Analyzer

A small desktop application that extracts text from a PDF or DOCX CV, calculates a transparent heuristic ATS score, compares it with an optional job description, and suggests improvements. Processing happens locally; uploaded files are placed in a temporary folder and removed after each analysis.

> The scores are guidance only. They do not reproduce a specific employer's applicant-tracking system and are not hiring decisions.

## Run from source

Requires Python 3.10 or newer on Windows.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

The desktop window uses pywebview and an internal Flask server bound only to a random local port.

## Build the Windows executable

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\build.ps1
```

The executable is written to `dist\AI-CV-Analyzer.exe`.

## Tests

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Safety limits

- PDF and DOCX only, up to 5 MB per upload
- Up to 50 PDF pages
- Up to 50 MB uncompressed DOCX content
- Up to 500,000 extracted characters
- Up to 50,000 characters in a job description
