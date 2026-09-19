# PocketLedger — AI financial certificate for informal traders

Built for **Hack for Humanity Harare 2026** (challenge: Best Use of the Google Gemini API).

## Problem and solution

Informal traders manage transactions using paper notebooks, which makes it hard to prove cash flow for micro-loans. PocketLedger uses Gemini Vision (`gemini-3.6-flash`) to scan handwritten ledgers, classify cash versus credit (*chikwereti*) sales, and generate a structured micro-business financial health certificate.

## Gemini integration and tech stack

- **Multimodal vision:** Reads non-standard layout entries from paper notebook photos.
- **Structured outputs:** Converts visual data into a JSON payload the app can display and download.
- **Stack:** Python, Streamlit, `google-genai` SDK, Pandas, Pillow.

## Run locally

1. `python -m venv .venv`
2. `.venv\Scripts\activate`
3. `pip install -r requirements.txt`
4. Optional: copy `.env.example` to `.env` and add `GEMINI_API_KEY`
5. `streamlit run app.py`

## Safeguards and limitations

PocketLedger is designed for preliminary record indexing. It does not replace a certified professional accounting audit. Images are processed in memory for the session and are not stored permanently.

## Hack Day build boundary

**Built today:** Streamlit UI, Gemini Vision prompts, JSON payload parser, metric dashboard, cash versus credit recalculation, 503 error handling, and a demo sample ledger generator.
