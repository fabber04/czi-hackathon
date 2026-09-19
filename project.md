# PocketLedger: Hack for Humanity 2026 Master Document

## 1. Project Design Framework

- **Official Challenge:** Best Use of the Google Gemini API.
- **The Problem:** Informal traders manage daily transactions and customer credit (*chikwereti*) on paper notebooks. Without organized records, they cannot prove cash flow to access micro-loans.
- **Primary User:** Informal market vendors, tuckshop operators, and micro-entrepreneurs.
- **Gemini Capability:** Multimodal Vision (`gemini-3.6-flash`) used to parse handwriting, extract line items, and generate a structured JSON summary.
- **Safeguards:** UI disclaimers state the generated summary is AI-assisted indexing, not an official tax audit.

---



## 2. Project Workspace Files

Create these files inside your `pocketledger-gemini` workspace folder.

### `requirements.txt`

```text
streamlit
google-genai
python-dotenv
pillow
pandas

```



### `.gitignore`

```text
.venv/
.env
__pycache__/
*.pyc
.DS_Store

```



### `.env.example`

```text
GEMINI_API_KEY=your_gemini_api_key_here

```



### `test_gemini.py`

Run this independent script first to verify your virtual environment and API access before testing the main app.

```python
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ GEMINI_API_KEY not found. Enter key manually or check .env file.")
else:
    try:
        client = genai.Client(api_key=api_key)
        interaction = client.interactions.create(
            model="gemini-3.6-flash",
            input="Confirm API connection for PocketLedger hackathon project in one sentence."
        )
        print("✅ API Connection Successful!")
        print("Response:", interaction.output_text)
    except Exception as e:
        print("❌ Error testing Gemini API:", str(e))

```



### `app.py`

This is your main Streamlit application containing the core workflow, user inputs, Gemini prompt, and 503 error handling.

```python
import streamlit as st
import json
import pandas as pd
from PIL import Image
from google import genai

st.set_page_config(page_title="PocketLedger — AI Financial Certificate", page_icon="📒", layout="wide")

st.sidebar.title("📒 PocketLedger")
api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Enter your Google AI Studio API Key")

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Responsible AI & Safeguard")
st.sidebar.info("PocketLedger provides AI-assisted optical digitisation. Statements serve as preliminary proof-of-business for micro-finance evaluation and do not replace certified formal accounting audits.")

st.title("PocketLedger: Informal Business Digitisation")
st.write("Convert handwritten sales notebooks and receipts into structured financial certificates.")

tab1, tab2 = st.tabs(["📸 Upload Ledger / Photo", "🧪 Demo Sample Ledger"])
image_to_process = None

with tab1:
    uploaded_file = st.file_uploader("Upload a handwritten ledger image", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        image_to_process = Image.open(uploaded_file)
        st.image(image_to_process, caption="Uploaded Ledger Page", use_container_width=True)

with tab2:
    if st.button("Generate Sample Handwritten Ledger Canvas"):
        from PIL import ImageDraw, ImageFont
        img = Image.new('RGB', (600, 400), color=(255, 253, 240))
        d = ImageDraw.Draw(img)
        sample_text = (
            "MBARE TUCKSHOP LEDGER - 18 Sept 2026\n"
            "------------------------------------\n"
            "1. 2x Cooking Oil $7.00 (Cash)\n"
            "2. 1x Bread $1.20 (Cash)\n"
            "3. 10kg Maize Meal $6.50 (Credit - Mai Tinashe)\n"
            "4. 500g Sugar $1.50 (Cash)\n"
            "5. 2x Soap Bar $2.00 (Credit - Baba John)\n"
            "------------------------------------\n"
            "Paid Rent: $10.00"
        )
        d.text((20, 20), sample_text, fill=(20, 20, 80))
        image_to_process = img
        st.image(image_to_process, caption="Sample Ledger Generated", use_container_width=True)

if image_to_process is not None:
    if st.button("🔍 Process Ledger with Gemini Vision"):
        if not api_key:
            st.error("Please enter your Gemini API Key in the sidebar to proceed.")
        else:
            client = genai.Client(api_key=api_key)
            prompt = """
            You are PocketLedger AI, a financial auditing assistant for informal market traders in Zimbabwe.
            Analyze the provided image of a handwritten ledger or receipt page.
            Extract the financial data and return a strictly structured JSON object with the following keys:
            {
              "business_name": "Name of business or 'Unspecified'",
              "date": "Date of entry or 'Unspecified'",
              "transactions": [
                {"item": "item name", "quantity": "qty", "amount_usd": 0.00, "payment_type": "Cash or Credit", "debtor": "person name if credit or N/A"}
              ],
              "total_revenue_usd": 0.00,
              "total_cash_usd": 0.00,
              "total_credit_outstanding_usd": 0.00,
              "business_health_summary": "2-sentence summary of cash flow and credit risk."
            }
            Do not include markdown code fence formatting like ```json. Return pure JSON text only.
            """
            
            with st.spinner("Extracting transactions and computing cash flow metrics..."):
                try:
                    interaction = client.interactions.create(
                        model="gemini-3.6-flash",
                        input=[prompt, image_to_process]
                    )
                    
                    response_text = interaction.output_text.strip()
                    if response_text.startswith("```"): response_text = response_text.split("\n", 1)[1]
                    if response_text.endswith("```"): response_text = response_text.rsplit("\n", 1)[0]
                    
                    data = json.loads(response_text)
                    st.success("Ledger Processed Successfully!")
                    st.markdown("---")
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Recorded Revenue", f"${data.get('total_revenue_usd', 0.0):.2f}")
                    col2.metric("Cash Received", f"${data.get('total_cash_usd', 0.0):.2f}")
                    col3.metric("Outstanding Credit (Chikwereti)", f"${data.get('total_credit_outstanding_usd', 0.0):.2f}")
                    
                    st.subheader("📊 Extracted Itemized Transactions")
                    st.dataframe(pd.DataFrame(data.get("transactions", [])), use_container_width=True)
                    
                    st.subheader("📋 Financial Health Certificate Assessment")
                    st.write(data.get("business_health_summary", "Summary unavailable."))
                    
                    st.download_button(
                        label="📥 Download Verified Ledger Payload (JSON)",
                        data=json.dumps(data, indent=2),
                        file_name="pocketledger_statement.json",
                        mime="application/json"
                    )
                except Exception as e:
                    err_msg = str(e)
                    if "503" in err_msg or "overloaded" in err_msg.lower():
                        st.error("⚠️ Gemini API is experiencing high demand (503). Please wait a moment and try again.")
                    else:
                        st.error(f"Error processing ledger image: {err_msg}")

```



### `README.md`

```markdown
# PocketLedger — AI Financial Certificate for Informal Traders

Built for **Hack for Humanity Harare 2026** (Challenge: Best Use of the Google Gemini API).

## Problem & Solution
Informal traders manage transactions using paper notebooks, preventing them from proving cash flow to access micro-loans. PocketLedger uses Gemini Vision (`gemini-3.6-flash`) to scan handwritten ledgers, classify cash vs. credit sales, and generate a structured **Micro-Business Financial Health Certificate**.

## Gemini Integration & Tech Stack
*   **Multimodal Vision:** Evaluates non-standard layout entries from paper notebook images.
*   **Structured Outputs:** Converts raw visual data into validated JSON payloads.
*   **Stack:** Python, Streamlit, `google-genai` SDK, Pandas, Pillow.

## Run Locally
1. `python -m venv .venv`
2. `.venv\Scripts\activate`
3. `pip install -r requirements.txt`
4. `streamlit run app.py`

## Safeguards & Limitations
PocketLedger is designed for preliminary record indexing. It does not replace certified professional accounting audits. No financial images are stored permanently.

## Hack Day Build Boundary
*   **Built Today:** Streamlit UI, Gemini Vision prompts, JSON payload parser, metric extraction dashboard, 503 error handling, and demo sample generator.

```

---



## 3. Submission & Demo Workflow



### Build Schedule Alignment

- **12:15–14:00 | Domain Logic:** Ensure the app accurately calculates cash vs. credit from your prompt.
- **14:00–15:00 | Resilience:** Test the empty input validation and 503 error catching.
- **15:00–16:00 | Documentation:** Finalize `README.md` and push clean code to GitHub (ensure `.env` is ignored).
- **16:00–17:30 | Submission:** Prepare your OrganizerHQ link and rehearse the demo.



### 2-Minute MLH Pitch Script

- **0:00–0:20 (Problem):** "70% of micro-traders track finances on paper, meaning they get rejected for micro-loans because they lack verifiable records."
- **0:20–0:40 (User & Input):** "PocketLedger turns any paper notebook into a digital financial certificate instantly."
- **0:40–1:30 (Live Demo):** *Click the 'Generate Sample' tab, run the process, and show the dashboard metrics.*
- **1:30–2:00 (Gemini Integration):** "We use `gemini-3.6-flash` vision to read non-standard handwriting and generate a structured JSON cashflow summary."
- **2:00–2:30 (Safeguards & Learnings):** "We built in 503 error handling for network resilience and added clear UI disclaimers regarding its status as an indexing tool, not an audit."

