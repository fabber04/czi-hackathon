# Hack for Humanity Harare 2026 | Beginner Build-Day Guide

From opening your laptop at 08:30 to a working Gemini-powered prototype and a submission-ready demo.

Saturday, 19 September 2026 | CZI, Harare | 08:30–17:30

Official challenge: **Best Use of the Google Gemini API**

Prepared as a practical participant handbook based on the actual setup difficulties encountered during the Harare hackathon build.

AI Collective Harare × Major League Hacking

## What this guide is for

This guide is written for a participant who may be completely new to APIs, virtual environments, VS Code, requirements files, Streamlit, GitHub and Gemini integration. It follows a simple local Windows workflow and explains not only what to type, but why each step exists.

## How to use this guide

You do not need to read this document from cover to cover before coding. Use the Day Map first, then follow the numbered steps in order. The guide assumes Windows 10/11 because that is the most common path used in the worked example. Mac and Linux commands are included in an appendix.

**Beginner rule:** Do not try to understand everything before starting. Complete one small step, confirm that it works, and only then move to the next step. A working simple prototype is far more valuable than an ambitious project that never runs.

## 1. The challenge in plain English

The hackathon challenge is not simply to ask Gemini questions or use Gemini to help write code. The project should contain an actual Gemini API integration inside the prototype. By demo time, a team should be able to show the human problem, the intended user, what was built during the day, exactly where Gemini is used, what the Gemini capability adds, what works, and what limitations or safeguards were considered.

**Simplest mental model:** Your app collects something from the user → your Python code sends relevant information to Gemini through an API → Gemini returns something useful → your app displays or uses that response.

```
USER -> STREAMLIT WEB PAGE -> PYTHON -> GEMINI API -> PYTHON -> STREAMLIT RESULT
```

### What the judges care about

MLH uses four equally weighted areas: Technology, Design, Completion and Learning. A small prototype that works and is easy to explain can perform better than a very large unfinished system.

| Area | Beginner interpretation |
| --- | --- |
| Technology | Does the project genuinely use the Gemini API and does the technical implementation work? |
| Design | Can a real user understand what to do and why the output is useful? |
| Completion | Can you demonstrate the core flow successfully rather than only describe it? |
| Learning | Can you explain what you tried, what failed, what you changed and what you learned? |

### Your minimum viable hack

- One human problem. Do not solve five problems.
- One primary user. Know exactly who uses the prototype.
- One meaningful Gemini capability. Use the API where it genuinely helps.
- One main workflow. Input → Gemini-assisted processing → useful output.
- One working demo. You should be able to repeat it in front of judges.

## 2. The 08:30–17:30 beginner day map

| Time | Focus | What you do | Milestone |
| --- | --- | --- | --- |
| 08:30–08:45 | Choose the problem | Write one sentence: user + problem + how Gemini helps. No coding yet. | |
| 08:45–09:30 | Set up the laptop | Confirm/install Python, VS Code, Python extension and Gemini API access. | Do not lose hours fighting tools silently; ask for help. |
| 09:30–09:50 | Create project | Create folder, files, virtual environment and install packages. | Project skeleton exists. |
| 09:50–10:05 | Hello World | Run a tiny Streamlit app. | Browser opens on localhost. |
| 10:05–10:25 | Test Gemini | Run one Python request to Gemini. | You know the API key and SDK work. |
| 10:25–12:00 | Build core workflow | Build one input → Gemini → output flow. | First working MVP. |
| 12:00–12:15 | Checkpoint | Demo it to a teammate exactly as a judge would see it. | Find blockers early. |
| 12:15–14:00 | Make it useful | Add the domain logic, prompts, simple validation and one strong scenario. | Core value visible. |
| 14:00–15:00 | Improve UX and safeguards | Labels, instructions, loading messages, limitations, API error handling. | Demo no longer feels fragile. |
| 15:00–16:00 | Test and document | Test normal and failure cases; prepare README; clean repo. | Repeatable build. |
| 16:00–16:45 | Submission package | Repo link, description, technologies, team, challenge selection. | Submission-ready. |
| 16:45–17:15 | Rehearse demo | Practice a 2–3 minute demonstration twice. | Everyone knows who says what. |
| 17:15–17:30 | Final check | Submit before the organizer-announced deadline; keep backup screenshots. | Done. |

## 3–12. Environment, Streamlit, and Gemini starter

This folder already contains the starter files from the handbook:

- `app.py` — Streamlit UI + Gemini API call + error handling
- `test_gemini.py` — independent API test
- `requirements.txt` — streamlit, google-genai, python-dotenv
- `.gitignore` — keeps `.venv` and `.env` off GitHub
- `.env.example` — safe template for `GEMINI_API_KEY`
- `README.md` — project explanation and run instructions

### Commands (Windows, from this folder)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

PowerShell activation: `.venv\Scripts\Activate.ps1`

### Gemini API key (do not buy a plan just to start)

1. Open [Google AI Studio](https://aistudio.google.com/) and sign in.
2. If Playground asks you to upgrade, go to **Dashboard → API Keys**.
3. Prefer a project marked **Free tier**. Do not click **Set up billing** merely because the link is visible.
4. Create an API key, copy it, and paste it into the app sidebar (or a local `.env` file).
5. Never post the full key in WhatsApp, screenshots, public GitHub, or slides.

Official docs:

- [API keys](https://ai.google.dev/gemini-api/docs/api-key)
- [Billing](https://ai.google.dev/gemini-api/docs/billing)

## 13. Turn the starter into your actual hack

Use this worksheet. Do not add features randomly.

| Question | Team answer |
| --- | --- |
| Problem | What specific human problem are we addressing? |
| User | Who will actually use this prototype? |
| Evidence | What tells us this is a real problem? |
| Current approach | How is the problem handled now? |
| Gap | What is missing or inefficient? |
| Gemini role | What can Gemini do here that genuinely helps? |
| Input | What will the user provide to the app? |
| Output | What useful result will the app return? |
| Safeguard | What could go wrong, and how will the prototype limit or communicate that risk? |
| Demo | What exact 60–120 second user journey will we show? |

Choose **one** Gemini capability: text reasoning, structured outputs, document understanding, image understanding, function calling, or RAG/file search. You do not need every capability.

## 14. Beginner development loop

1. Make ONE small change.
2. Save the file.
3. Let Streamlit rerun (or rerun manually).
4. Test the feature.
5. If it breaks, fix that small change before adding another.
6. Commit to Git when the project reaches a working checkpoint.

## 15. Failures to handle

| Test | Expected behaviour |
| --- | --- |
| No API key | App explains that a key is required instead of crashing. |
| Empty user input | App asks the user to provide input. |
| Gemini temporarily unavailable | Friendly retry message appears. |
| Very long response | Page remains readable. |
| Bad/irrelevant input | Prompt or interface guides user back to intended use. |
| Refresh browser | You understand what state is retained and what is lost. |
| Internet drops | Team knows the app requires connectivity and has screenshots. |

HTTP 503 generally means the service is temporarily unavailable. It does not necessarily mean your API key, code or account is wrong.

## 16. GitHub and README

**Do not upload:** `.env`, `.venv/`, or your real API key.

README should include: project name, problem and user, what was built today, exactly how Gemini is used, tech stack, run instructions, limitations, team members, and any pre-existing material.

## 17. Demo (2–3 minutes)

| Time | What to show | What to say |
| --- | --- | --- |
| 0:00–0:20 | Problem | Who is affected and why this matters. |
| 0:20–0:40 | User + input | What the user gives the application. |
| 0:40–1:30 | Live workflow | Show the actual working app, not only slides. |
| 1:30–2:00 | Gemini integration | Point to the exact step where your app calls Gemini. |
| 2:00–2:30 | Output / impact | Why the result is useful. |
| 2:30–2:50 | Risk / safeguard | What could go wrong and how you bounded it. |
| 2:50–3:00 | Learning | One thing that failed or changed. |

Submit through OrganizerHQ and select **Best Use of the Google Gemini API**.

## Appendix A. Command cheat sheet

| Command | Meaning |
| --- | --- |
| `python --version` | Check whether Python is installed. |
| `pip --version` | Check whether pip is installed. |
| `python -m venv .venv` | Create a private Python environment. |
| `.venv\Scripts\activate` | Activate `.venv` in Windows Command Prompt. |
| `pip install -r requirements.txt` | Install packages. |
| `streamlit run app.py` | Start the app. |
| `Ctrl + C` | Stop Streamlit. |
| `deactivate` | Leave the virtual environment. |

## Appendix C. Mac / Linux

| Task | Windows | macOS / Linux |
| --- | --- | --- |
| Create venv | `python -m venv .venv` | `python3 -m venv .venv` |
| Activate venv | `.venv\Scripts\activate` | `source .venv/bin/activate` |
| Install packages | `pip install -r requirements.txt` | same |
| Run app | `streamlit run app.py` | same |

## Appendix D. Troubleshooting

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| `python` is not recognized | Python missing or not on PATH | Install Python; tick Add python.exe to PATH; reopen terminal. |
| No `(.venv)` in prompt | venv not active | Run `.venv\Scripts\activate`. |
| `streamlit` is not recognized | Wrong environment | Activate `.venv`, reinstall, or `python -m streamlit run app.py`. |
| AI Studio asks for upgrade | Playground gated | Use Dashboard → API Keys; check Billing Tier. |
| Gemini 401/403 | Key or permission issue | Recheck the key; do not expose it while asking for help. |
| Gemini 429 | Rate limit | Wait; reduce request frequency. |
| Gemini 503 | High demand | Wait and retry; friendly error handling is already in `app.py`. |
| Key pushed to GitHub | Credential exposure | Revoke/replace the key immediately. |

## Official resources

- [Google AI Studio](https://aistudio.google.com/)
- [Gemini API docs](https://ai.google.dev/gemini-api/docs)
- [Streamlit install](https://docs.streamlit.io/get-started/installation/command-line)
- [VS Code Python tutorial](https://code.visualstudio.com/docs/python/python-tutorial)
- [Python Windows downloads](https://www.python.org/downloads/windows/)
- [MLH standard hackathon rules](https://github.com/MLH/mlh-policies/blob/main/standard-hackathon-rules.md)

## Final beginner checklist

- [ ] I can explain the human problem in one sentence.
- [ ] I know who the intended user is.
- [ ] Python and pip work.
- [ ] VS Code is open on the correct project folder.
- [ ] My `.venv` is active.
- [ ] `requirements.txt` installs successfully.
- [ ] `streamlit run app.py` opens my application.
- [ ] My Gemini API key works and is not inside public source code.
- [ ] I can point to the exact place where my app uses the Gemini API.
- [ ] The core demo works end to end.
- [ ] The app handles a missing key and empty input without crashing.
- [ ] I know what happens if Gemini returns an API error.
- [ ] My GitHub repository does not contain `.env`, `.venv` or a real key.
- [ ] My README explains how to run the project.
- [ ] My team has rehearsed the demonstration.
- [ ] We know the OrganizerHQ submission deadline announced by organisers.
