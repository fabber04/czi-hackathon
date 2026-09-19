# Hack for Humanity Harare 2026 — Gemini Starter

A beginner Streamlit prototype that sends a human-problem description to the Gemini API and displays a structured response.

## Problem

Replace this with the specific human problem your team chose, and name the intended user.

## Solution

A local Streamlit app: user input → Python → Gemini API → useful output in the browser.

## Gemini integration

`app.py` calls `client.interactions.create()` with `gemini-3.6-flash` when the user clicks **Ask Gemini**. That runtime API call is the challenge requirement — Gemini is not only used to write code.

## Tech stack

- Python
- Streamlit
- google-genai
- python-dotenv

## Run locally (Windows)

1. `python -m venv .venv`
2. `.venv\Scripts\activate` (Command Prompt) or `.venv\Scripts\Activate.ps1` (PowerShell)
3. `pip install -r requirements.txt`
4. Optional: copy `.env.example` to `.env` and add `GEMINI_API_KEY`
5. `streamlit run app.py`
6. Paste the API key in the sidebar if it is not already in `.env`

Test the API without Streamlit:

```
python test_gemini.py
```

## Safeguards and limitations

- Do not put a real API key in source files or GitHub.
- The app needs internet access.
- Gemini can be temporarily unavailable (HTTP 503 / high demand). Retry rather than assuming the key is wrong.
- Output is assistance, not professional advice.

## Hack-Day build boundary

Starter files in this folder were set up from the beginner build-day guide. The team's own problem, prompts, and domain logic should be added on top of this skeleton.

## Team members

Add names here.
