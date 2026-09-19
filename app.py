import base64
import io
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from fpdf import FPDF
from google import genai
from PIL import Image, ImageDraw, ImageOps

load_dotenv()

MODEL_NAME = "gemini-3.6-flash"
BUSINESS_CATEGORIES = [
    "Tuckshop / grocery",
    "Fresh produce / market stall",
    "Clothing and textiles",
    "Fast food / kitchen",
    "Hair and beauty",
    "Airtime, phones, and electronics",
    "Hardware and building supplies",
    "Agriculture and livestock",
    "Transport and logistics",
    "Repairs and other services",
    "Cross-border trading",
    "Other",
]


def extraction_prompt(business_name: str, category: str, source: str = "image") -> str:
    context_lines = []
    if category:
        context_lines.append(f"The trader selected this business category: {category}.")
    if business_name:
        context_lines.append(
            f"The onboarded business name is: {business_name}. "
            "Use it unless the recording or page clearly shows a different name."
        )
    context = " ".join(context_lines)
    if source == "audio":
        analyze = (
            "Listen to the trader dictating their day's sales, cash, chikwereti (credit), "
            "and expenses. They may speak English, ChiShona, IsiNdebele, or a mix."
        )
        invent_rule = (
            "- Do not invent line items that were not spoken. "
            "If an amount is unclear, omit that line rather than guessing."
        )
        transcript_key = '  "transcript": "Near-verbatim transcription of the spoken statement",\n'
    else:
        analyze = "Analyze the provided image of a handwritten ledger or receipt page."
        invent_rule = "- Do not invent line items that are not visible."
        transcript_key = ""
    return f"""
You are PocketLedger AI, a financial indexing assistant for informal market traders in Zimbabwe.
{context}
{analyze}
Extract the financial data and return a strictly structured JSON object with the following keys:
{{
  "business_name": "Name of business or 'Unspecified'",
  "date": "Date of entry or 'Unspecified'",
{transcript_key}  "transactions": [
    {{"item": "item name", "quantity": "qty", "amount_usd": 0.00, "payment_type": "Cash or Credit", "debtor": "person name if credit or N/A"}}
  ],
  "total_revenue_usd": 0.00,
  "total_cash_usd": 0.00,
  "total_credit_outstanding_usd": 0.00,
  "business_health_summary": "2-sentence summary of cash flow and credit risk, considering the business category.",
  "summary_shona": "2 short sentences in simple everyday ChiShona. Use words like mari, cash, chikwereti. Include the USD amounts.",
  "summary_ndebele": "2 short sentences in simple everyday IsiNdebele. Use words like imali, cash, isikwelete. Include the USD amounts."
}}
Rules:
- Treat Credit / chikwereti / named debtors as outstanding credit, not cash.
- Amounts are in USD.
- Paid rent and similar operating costs are expenses, not sales. Put them in transactions with payment_type "Expense" so they are excluded from cash and credit sales totals.
- Interpret items in the context of the selected business category.
- Write summary_shona and summary_ndebele in spoken market language, not formal or literary style.
{invent_rule}
- Do not include markdown code fences. Return pure JSON text only.
"""


MAX_LEDGER_SIDE = 1024
JPEG_QUALITY = 70


def format_bytes(size: int) -> str:
    if size < 1024 * 1024:
        return f"{max(1, round(size / 1024))} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def prepare_ledger_image(image: Image.Image) -> Image.Image:
    rgb = ImageOps.exif_transpose(image).convert("RGB")
    width, height = rgb.size
    longest = max(width, height)
    if longest <= MAX_LEDGER_SIDE:
        return rgb
    scale = MAX_LEDGER_SIDE / longest
    return rgb.resize(
        (max(1, int(width * scale)), max(1, int(height * scale))),
        Image.Resampling.LANCZOS,
    )


def encode_ledger_jpeg(image: Image.Image, quality: int = JPEG_QUALITY) -> bytes:
    buffer = io.BytesIO()
    prepare_ledger_image(image).save(
        buffer, format="JPEG", quality=quality, optimize=True
    )
    return buffer.getvalue()


def bytes_to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def audio_mime_for(filename: str, reported: str | None) -> str:
    reported = (reported or "").lower()
    name = (filename or "").lower()
    if "mpeg" in reported or name.endswith(".mp3"):
        return "audio/mp3"
    if "m4a" in reported or name.endswith(".m4a") or "mp4" in reported:
        return "audio/m4a"
    if "webm" in reported or name.endswith(".webm"):
        return "audio/webm"
    if "ogg" in reported or name.endswith(".ogg"):
        return "audio/ogg"
    return "audio/wav"


def parse_json_payload(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("Gemini did not return JSON.")
    return json.loads(cleaned[start : end + 1])


def to_float(value: Any) -> float:
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def recompute_totals(transactions: list[dict[str, Any]]) -> tuple[float, float, float]:
    cash = 0.0
    credit = 0.0
    for row in transactions:
        amount = to_float(row.get("amount_usd"))
        payment = str(row.get("payment_type") or "").lower()
        if "expense" in payment or "rent" in payment:
            continue
        if "credit" in payment or "chikwereti" in payment:
            credit += amount
        else:
            cash += amount
    return cash + credit, cash, credit


def _plain(value: Any) -> str:
    return "" if value is None else str(value).replace("\x00", "").strip()


def _money(value: Any) -> str:
    return f"${to_float(value):,.2f}"


def local_language_summaries(result: dict[str, Any]) -> dict[str, str]:
    revenue = _money(result.get("total_revenue_usd"))
    cash = _money(result.get("total_cash_usd"))
    credit = _money(result.get("total_credit_outstanding_usd"))
    cash_val = to_float(result.get("total_cash_usd"))
    credit_val = to_float(result.get("total_credit_outstanding_usd"))

    shona = (
        f"Bhizinesi rako nhasi rakawana mari inosvika {revenue}. "
        f"Yakabhadharwa cash ndeye {cash}. "
        f"Chikwereti chakasara, vanhu vasina kubhadhara, ndeche {credit}."
    )
    if credit_val > cash_val:
        shona += " Chikwereti chakawanda kupfuura cash, saka tsvaka vanhu vabhadhare kuti bhizinesi rifambe."
    elif credit_val > 0:
        shona += " Rangarira kutevera vanhu vane chikwereti."
    else:
        shona += " Hapana chikwereti chakakura nhasi."

    ndebele = (
        f"Ibizinisi lakho namhlanje lithole imali efika ku {revenue}. "
        f"Imali ekhokhiwe ngokheshi ngu {cash}. "
        f"Isikwelete esisele, abantu abangakhokhanga, ngu {credit}."
    )
    if credit_val > cash_val:
        ndebele += " Isikwelete sikhulu kunemali ekhokhiwe, ngakho cela ukuthi bakhokhe ukuze ibhizinisi liqhubeke."
    elif credit_val > 0:
        ndebele += " Khumbula ukulandela abantu abakweletayo."
    else:
        ndebele += " Asikho isikwelete esikhulu namhlanje."

    return {"summary_shona": shona, "summary_ndebele": ndebele}


def attach_local_summaries(result: dict[str, Any]) -> dict[str, Any]:
    fallback = local_language_summaries(result)
    shona = _plain(result.get("summary_shona"))
    ndebele = _plain(result.get("summary_ndebele"))
    result["summary_shona"] = shona if len(shona) > 20 else fallback["summary_shona"]
    result["summary_ndebele"] = ndebele if len(ndebele) > 20 else fallback["summary_ndebele"]
    return result


def apply_extraction_result(data: dict[str, Any], capture_source: str) -> dict[str, Any]:
    transactions = data.get("transactions") or []
    revenue, cash, credit = recompute_totals(transactions)
    data["total_revenue_usd"] = round(revenue, 2)
    data["total_cash_usd"] = round(cash, 2)
    data["total_credit_outstanding_usd"] = round(credit, 2)
    data["business_category"] = st.session_state.business_category
    data["capture_source"] = capture_source
    onboard_name = st.session_state.business_name
    extracted_name = _plain(data.get("business_name"))
    if onboard_name and (not extracted_name or extracted_name == "Unspecified"):
        data["business_name"] = onboard_name
    attach_local_summaries(data)
    data["transcript"] = _plain(data.get("transcript"))
    return data


def extract_structured_ledger(
    client: Any,
    prompt: str,
    media: dict[str, Any],
    *,
    spinner: str,
    capture_source: str,
) -> None:
    with st.spinner(spinner):
        try:
            from ledger_core import run_gemini_extraction

            data = run_gemini_extraction(client, prompt, media)
            st.session_state.result = apply_extraction_result(data, capture_source)
            persist_ledger(st.session_state.result)
            st.toast("Ledger saved to this trader's history.", icon=":material/check_circle:")
        except Exception as error:
            from ledger_core import friendly_gemini_error, is_rate_limit_error

            message = friendly_gemini_error(error)
            if is_rate_limit_error(error) or "quota" in message.lower():
                st.error(message)
            elif "503" in message or "overloaded" in message.lower():
                st.error(message)
            else:
                st.error(f"Error processing the statement: {message}")


def projection_local_summaries(week_revenue: float, week_cash: float, next_credit: float) -> dict[str, str]:
    return {
        "English": (
            f"If this pattern continues, the next 7 days may bring about {_money(week_revenue)} in sales "
            f"and {_money(week_cash)} in cash. Outstanding credit could sit near {_money(next_credit)}."
        ),
        "ChiShona": (
            f"Kana zikaramba zvakadai, mazuva manomwe anotevera unogona kuwana mari yekutengesa inosvika {_money(week_revenue)} "
            f"uye cash inosvika {_money(week_cash)}. Chikwereti chingasara chiri pedyo ne {_money(next_credit)}."
        ),
        "IsiNdebele": (
            f"Uma kuqhubeka kanje, ezinsukwini eziyisikhombisa ezizayo ungathola imali yokuthengisa efika ku {_money(week_revenue)} "
            f"kanye nemali ekhokhiwe efika ku {_money(week_cash)}. Isikwelete singahlala eduze kwe {_money(next_credit)}."
        ),
    }


def _register_pdf_font(pdf: FPDF) -> str:
    win_fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    regular = win_fonts / "arial.ttf"
    bold = win_fonts / "arialbd.ttf"
    if regular.exists():
        pdf.add_font("AppSans", "", str(regular))
        pdf.add_font("AppSans", "B", str(bold if bold.exists() else regular))
        return "AppSans"
    return "Helvetica"


def build_statement_pdf(result: dict[str, Any]) -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    font_name = _register_pdf_font(pdf)
    navy = (28, 32, 80)
    muted = (90, 95, 120)

    pdf.set_text_color(*navy)
    pdf.set_font(font_name, "B", 18)
    pdf.cell(0, 10, "PocketLedger financial certificate", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(font_name, "", 11)
    pdf.set_text_color(*muted)
    pdf.cell(0, 6, "AI-assisted cash versus credit statement", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    business = _plain(result.get("business_name", "Unspecified")) or "Unspecified"
    date = _plain(result.get("date", "Unspecified")) or "Unspecified"
    category = _plain(result.get("business_category"))
    pdf.set_text_color(*navy)
    pdf.set_font(font_name, "B", 14)
    pdf.cell(0, 8, f"{business}  ·  {date}", new_x="LMARGIN", new_y="NEXT")
    if category:
        pdf.set_font(font_name, "", 11)
        pdf.set_text_color(*muted)
        pdf.cell(0, 6, f"Category: {category}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font(font_name, "", 11)
    for label, key in (
        ("Total recorded revenue", "total_revenue_usd"),
        ("Cash received", "total_cash_usd"),
        ("Outstanding credit (chikwereti)", "total_credit_outstanding_usd"),
    ):
        pdf.set_font(font_name, "B", 11)
        pdf.cell(88, 7, label)
        pdf.set_font(font_name, "", 11)
        pdf.cell(0, 7, _money(result.get(key)), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font(font_name, "B", 13)
    pdf.cell(0, 8, "Extracted transactions", new_x="LMARGIN", new_y="NEXT")
    transactions = result.get("transactions") or []
    if not transactions:
        pdf.set_font(font_name, "", 11)
        pdf.cell(0, 7, "No line items extracted.", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font(font_name, "", 9)
        with pdf.table(col_widths=(52, 22, 28, 38, 40), text_align=("LEFT", "CENTER", "RIGHT", "LEFT", "LEFT")) as table:
            header = table.row()
            for title in ("Item", "Qty", "Amount (USD)", "Payment type", "Debtor"):
                header.cell(title)
            for row in transactions:
                cells = table.row()
                cells.cell(_plain(row.get("item")) or "—")
                cells.cell(_plain(row.get("quantity")) or "—")
                cells.cell(_money(row.get("amount_usd")))
                cells.cell(_plain(row.get("payment_type")) or "—")
                cells.cell(_plain(row.get("debtor")) or "N/A")

    pdf.ln(6)
    pdf.set_font(font_name, "B", 13)
    pdf.set_text_color(*navy)
    pdf.cell(0, 8, "Financial health certificate", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(font_name, "", 11)
    summary = _plain(result.get("business_health_summary")) or "Summary unavailable."
    pdf.multi_cell(0, 6, summary)
    pdf.ln(3)
    pdf.set_font(font_name, "B", 12)
    pdf.cell(0, 7, "ChiShona", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(font_name, "", 11)
    pdf.multi_cell(0, 6, _plain(result.get("summary_shona")) or "Hapana pfupiso.")
    pdf.ln(2)
    pdf.set_font(font_name, "B", 12)
    pdf.cell(0, 7, "IsiNdebele", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(font_name, "", 11)
    pdf.multi_cell(0, 6, _plain(result.get("summary_ndebele")) or "Asikho isifinyezo.")
    pdf.ln(4)
    pdf.set_font(font_name, "", 9)
    pdf.set_text_color(*muted)
    pdf.multi_cell(
        0,
        5,
        "AI-assisted indexing only. Totals are recalculated from extracted line items. "
        "This is not an IT audit, tax audit, or certified financial report, and it is not a loan decision.",
    )
    return bytes(pdf.output())


def statement_pdf_filename(result: dict[str, Any]) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", _plain(result.get("business_name")).lower()).strip("_")
    return f"pocketledger_{slug or 'statement'}.pdf"


DATA_DIR = Path(__file__).resolve().parent / "data"
STORE_PATH = DATA_DIR / "ledger_store.json"


def user_id_for(name: str, category: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", f"{name}_{category}".lower()).strip("_")
    return slug or "unnamed_trader"


def load_store() -> dict[str, Any]:
    if STORE_PATH.exists():
        try:
            return json.loads(STORE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"users": {}, "last_user_id": None}
    return {"users": {}, "last_user_id": None}


def save_store(store: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def persist_user_profile() -> None:
    store = load_store()
    uid = st.session_state.user_id
    users = store.setdefault("users", {})
    profile = users.setdefault(uid, {"ledgers": []})
    profile["business_name"] = st.session_state.business_name
    profile["business_category"] = st.session_state.business_category
    store["last_user_id"] = uid
    save_store(store)


def persist_ledger(result: dict[str, Any]) -> None:
    snapshot = {
        "processed_at": datetime.now().isoformat(timespec="seconds"),
        "business_name": result.get("business_name"),
        "business_category": result.get("business_category"),
        "date": result.get("date"),
        "capture_source": result.get("capture_source"),
        "transcript": result.get("transcript"),
        "total_revenue_usd": round(to_float(result.get("total_revenue_usd")), 2),
        "total_cash_usd": round(to_float(result.get("total_cash_usd")), 2),
        "total_credit_outstanding_usd": round(to_float(result.get("total_credit_outstanding_usd")), 2),
        "transactions": result.get("transactions") or [],
        "business_health_summary": result.get("business_health_summary"),
        "summary_shona": result.get("summary_shona"),
        "summary_ndebele": result.get("summary_ndebele"),
    }
    store = load_store()
    uid = st.session_state.user_id
    users = store.setdefault("users", {})
    profile = users.setdefault(
        uid,
        {
            "business_name": st.session_state.business_name,
            "business_category": st.session_state.business_category,
            "ledgers": [],
        },
    )
    profile.setdefault("ledgers", []).append(snapshot)
    store["last_user_id"] = uid
    save_store(store)
    st.session_state.saved_ledgers = profile["ledgers"]


def restore_last_user() -> None:
    if st.session_state.onboarded:
        return
    store = load_store()
    uid = store.get("last_user_id")
    users = store.get("users") or {}
    profile = users.get(uid) if uid else None
    if not profile:
        return
    st.session_state.onboarded = True
    st.session_state.user_id = uid
    st.session_state.business_name = profile.get("business_name") or ""
    st.session_state.business_category = profile.get("business_category") or ""
    st.session_state.saved_ledgers = profile.get("ledgers") or []


def payment_mix_df(transactions: list[dict[str, Any]]) -> pd.DataFrame:
    if not transactions:
        return pd.DataFrame()
    rows = pd.DataFrame(transactions)
    if "payment_type" not in rows.columns:
        rows["payment_type"] = "Unspecified"
    rows["Amount"] = rows["amount_usd"].map(to_float) if "amount_usd" in rows.columns else 0.0
    mix = (
        rows.assign(**{"Payment type": rows["payment_type"].fillna("Unspecified").astype(str)})
        .groupby("Payment type", dropna=False)["Amount"]
        .sum()
        .reset_index()
    )
    return mix[mix["Amount"] != 0]


def item_amount_df(transactions: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for row in transactions:
        amount = to_float(row.get("amount_usd"))
        if amount == 0:
            continue
        rows.append({"Item": _plain(row.get("item")) or "Unspecified", "Amount": amount})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).groupby("Item", as_index=False)["Amount"].sum().sort_values("Amount", ascending=False)


def _linear_forecast(values: list[float], steps: int) -> list[float]:
    n = len(values)
    if steps <= 0:
        return []
    if n == 0:
        return [0.0] * steps
    if n == 1:
        return [max(0.0, values[0])] * steps
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    var_x = sum((x - mean_x) ** 2 for x in xs)
    slope = 0.0 if var_x == 0 else sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)) / var_x
    intercept = mean_y - slope * mean_x
    return [round(max(0.0, intercept + slope * (n - 1 + step)), 2) for step in range(1, steps + 1)]


def history_and_projection_df(ledgers: list[dict[str, Any]], horizon: int = 7) -> pd.DataFrame:
    labels: list[str] = []
    revenues: list[float] = []
    cash: list[float] = []
    credit: list[float] = []
    kinds: list[str] = []
    for index, ledger in enumerate(ledgers, start=1):
        date_label = _plain(ledger.get("date")) or _plain(ledger.get("processed_at"))[:10] or f"Ledger {index}"
        labels.append(f"{index}. {date_label}")
        revenues.append(to_float(ledger.get("total_revenue_usd")))
        cash.append(to_float(ledger.get("total_cash_usd")))
        credit.append(to_float(ledger.get("total_credit_outstanding_usd")))
        kinds.append("Recorded")
    for step, (rev, cas, cred) in enumerate(
        zip(_linear_forecast(revenues, horizon), _linear_forecast(cash, horizon), _linear_forecast(credit, horizon)),
        start=1,
    ):
        labels.append(f"Day +{step}")
        revenues.append(rev)
        cash.append(cas)
        credit.append(cred)
        kinds.append("Projected")
    return pd.DataFrame(
        {
            "Period": labels,
            "Revenue": revenues,
            "Cash": cash,
            "Credit": credit,
            "Kind": kinds,
        }
    )


def brand_mark() -> Image.Image:
    img = Image.new("RGBA", (192, 192), (15, 42, 61, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((18, 18, 174, 174), radius=40, fill=(11, 110, 79, 255))
    draw.rectangle((50, 56, 142, 68), fill=(244, 247, 250, 255))
    draw.rectangle((50, 86, 142, 98), fill=(244, 247, 250, 210))
    draw.rectangle((50, 116, 108, 128), fill=(244, 247, 250, 170))
    return img


def current_summary_language() -> str:
    return st.session_state.get("summary_language") or "ChiShona"


st.set_page_config(
    page_title="PocketLedger",
    page_icon=":material/menu_book:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.session_state.setdefault("ledger_image", None)
st.session_state.setdefault("ledger_jpeg", None)
st.session_state.setdefault("ledger_caption", "")
st.session_state.setdefault("ledger_audio", None)
st.session_state.setdefault("ledger_audio_mime", "audio/wav")
st.session_state.setdefault("ledger_audio_id", "")
st.session_state.setdefault("result", None)
st.session_state.setdefault("onboarded", False)
st.session_state.setdefault("business_name", "")
st.session_state.setdefault("business_category", "")
st.session_state.setdefault("user_id", "")
st.session_state.setdefault("saved_ledgers", [])
restore_last_user()


@st.cache_resource
def get_gemini_client(api_key: str):
    return genai.Client(
        api_key=api_key,
        http_options={"timeout": 180_000},
    )


def resolve_api_key() -> str:
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key
    try:
        return str(st.secrets["GEMINI_API_KEY"]).strip()
    except Exception:
        return ""


st.logo(brand_mark(), size="large")
with st.sidebar:
    st.header("PocketLedger")
    st.caption("Cash versus chikwereti certificates for informal traders.")
    api_key = resolve_api_key()
    if api_key:
        st.badge("Gemini ready", icon=":material/check_circle:", color="green")
    else:
        api_key = st.text_input(
            "Gemini API key",
            type="password",
            help="Add GEMINI_API_KEY to a local .env file so you only set it once.",
        )
        st.caption("[Get an API key](https://aistudio.google.com/)")
    if st.session_state.onboarded:
        st.subheader("Business", divider="gray")
        st.markdown(f"**{st.session_state.business_name or 'Unnamed business'}**")
        st.selectbox(
            "Category",
            BUSINESS_CATEGORIES,
            placeholder="Choose a category",
            key="business_category",
            help="Used on the certificate and to give Gemini the right trade context.",
        )
        persist_user_profile()
        st.metric("Saved statements", len(st.session_state.saved_ledgers), border=True)
        st.selectbox(
            "Summary language",
            ["ChiShona", "IsiNdebele", "English"],
            key="summary_language",
            persist_state="session",
        )
    with st.expander("Responsible AI", icon=":material/shield:"):
        st.caption(
            "PocketLedger is AI-assisted indexing for micro-finance evaluation. "
            "It is not an IT audit, tax audit, or certified financial report, and it is not a loan decision."
        )

if not st.session_state.onboarded:
    left, mid, right = st.columns((1, 1.3, 1), gap="large")
    with mid:
        st.title("Set up your business", icon=":material/storefront:")
        st.caption("Choose the trade that matches this ledger. That category stays on the certificate.")
        with st.form("onboarding", border=True):
            st.text_input(
                "Business name",
                placeholder="e.g. Gogo Chipo fresh produce",
                key="onboard_business_name",
            )
            st.selectbox(
                "Business category",
                BUSINESS_CATEGORIES,
                index=None,
                placeholder="Choose a category",
                key="onboard_category",
                help="This stays on the financial certificate and helps Gemini read the ledger in context.",
            )
            submitted = st.form_submit_button(
                "Continue",
                type="primary",
                icon=":material/arrow_forward:",
                width="stretch",
            )
            if submitted:
                category = st.session_state.get("onboard_category")
                name = (st.session_state.get("onboard_business_name") or "").strip()
                if not category:
                    st.error("Please choose a business category from the menu.")
                else:
                    st.session_state.business_name = name
                    st.session_state.business_category = category
                    st.session_state.user_id = user_id_for(name, category)
                    st.session_state.onboarded = True
                    store = load_store()
                    existing = (store.get("users") or {}).get(st.session_state.user_id) or {}
                    st.session_state.saved_ledgers = existing.get("ledgers") or []
                    persist_user_profile()
                    st.rerun()
    st.stop()

st.title("PocketLedger", icon=":material/menu_book:")
st.caption("Turn a handwritten notebook page or a spoken statement into a cash-versus-credit certificate.")
with st.container(horizontal=True):
    if st.session_state.business_category:
        st.badge(st.session_state.business_category, icon=":material/category:", color="green")
    st.badge(
        f"{len(st.session_state.saved_ledgers)} saved",
        icon=":material/folder:",
        color="blue",
    )

with st.container(border=True):
    st.header("Capture a ledger", icon=":material/photo_camera:")
    st.caption("Upload a notebook photo from samples/ledgers, or speak the day's sales.")
    upload_tab, voice_tab = st.tabs(
        [
            ":material/upload: Upload photo",
            ":material/mic: Speak statement",
        ]
    )
    with upload_tab:
        uploaded_file = st.file_uploader(
            "Handwritten ledger image",
            type=["jpg", "jpeg", "png"],
            help="Phone photos are resized to 1024px and saved as JPEG on upload.",
        )
        if uploaded_file is not None:
            original = uploaded_file.getvalue()
            jpeg = encode_ledger_jpeg(Image.open(io.BytesIO(original)))
            st.session_state.ledger_jpeg = jpeg
            st.session_state.ledger_image = Image.open(io.BytesIO(jpeg)).convert("RGB")
            st.session_state.ledger_caption = (
                f"Compressed {format_bytes(len(original))} → {format_bytes(len(jpeg))}"
            )
            st.session_state.ledger_audio = None
            st.session_state.ledger_audio_id = ""
            st.session_state.result = None
    with voice_tab:
        st.caption(
            "Say the items, amounts, cash vs *chikwereti*, and who still owes you. "
            "English, ChiShona, or IsiNdebele is fine."
        )
        spoken = st.audio_input(
            "Record your statement",
            sample_rate=16000,
            help="16 kHz recording, sent to Gemini as audio. Not stored after this session.",
        )
        if spoken is not None and st.session_state.ledger_audio_id != spoken.file_id:
            st.session_state.ledger_audio = spoken.getvalue()
            st.session_state.ledger_audio_mime = "audio/wav"
            st.session_state.ledger_audio_id = spoken.file_id
            st.session_state.ledger_image = None
            st.session_state.ledger_jpeg = None
            st.session_state.ledger_caption = "Spoken statement"
            st.session_state.result = None
        uploaded_audio = st.file_uploader(
            "Or upload a voice note",
            type=["wav", "mp3", "m4a", "ogg", "webm"],
        )
        if uploaded_audio is not None:
            audio_id = getattr(uploaded_audio, "file_id", uploaded_audio.name)
            if st.session_state.ledger_audio_id != audio_id:
                st.session_state.ledger_audio = uploaded_audio.getvalue()
                st.session_state.ledger_audio_mime = audio_mime_for(
                    uploaded_audio.name, uploaded_audio.type
                )
                st.session_state.ledger_audio_id = audio_id
                st.session_state.ledger_image = None
                st.session_state.ledger_jpeg = None
                st.session_state.ledger_caption = f"Voice note: {uploaded_audio.name}"
                st.session_state.result = None

    ledger_image = st.session_state.ledger_image
    ledger_audio = st.session_state.ledger_audio
    if ledger_image is None and ledger_audio is None:
        st.caption("Upload a photo from samples/ledgers, or record a statement to start.")
    elif ledger_audio is not None:
        preview, actions = st.columns((1.25, 1), gap="large", vertical_alignment="top")
        with preview:
            st.audio(ledger_audio, format=st.session_state.ledger_audio_mime)
            st.caption(st.session_state.ledger_caption)
        with actions:
            st.subheader("Extract with Gemini", icon=":material/graphic_eq:")
            st.caption(
                "Gemini listens for items, cash versus *chikwereti*, and amounts, "
                "then returns JSON the app can verify."
            )
            if st.button(
                "Process spoken statement",
                type="primary",
                icon=":material/play_arrow:",
                width="stretch",
            ):
                if not api_key:
                    st.error("Add your Gemini API key in the sidebar.")
                else:
                    extract_structured_ledger(
                        get_gemini_client(api_key),
                        extraction_prompt(
                            st.session_state.business_name,
                            st.session_state.business_category,
                            source="audio",
                        ),
                        {
                            "type": "audio",
                            "data": bytes_to_b64(ledger_audio),
                            "mime_type": st.session_state.ledger_audio_mime,
                        },
                        spinner="Listening to the statement and checking cash versus credit...",
                        capture_source="audio",
                    )
    else:
        with st.container(horizontal=True, gap="large", vertical_alignment="center"):
            with st.container(border=True, width=228, horizontal_alignment="center"):
                st.image(
                    st.session_state.ledger_jpeg or ledger_image,
                    width=196,
                    output_format="JPEG",
                )
                st.badge("Ledger photo", icon=":material/photo:", color="blue")
                st.caption(st.session_state.ledger_caption)
            with st.container():
                st.subheader("Extract with Gemini", icon=":material/document_scanner:")
                st.caption(
                    "On upload the photo is reduced to 1024px JPEG. "
                    "Gemini still classifies cash versus *chikwereti*."
                )
                if st.button(
                    "Process ledger",
                    type="primary",
                    icon=":material/play_arrow:",
                    width="stretch",
                ):
                    if not api_key:
                        st.error("Add your Gemini API key in the sidebar.")
                    else:
                        jpeg_bytes = st.session_state.ledger_jpeg or encode_ledger_jpeg(
                            ledger_image
                        )
                        extract_structured_ledger(
                            get_gemini_client(api_key),
                            extraction_prompt(
                                st.session_state.business_name,
                                st.session_state.business_category,
                                source="image",
                            ),
                            {
                                "type": "image",
                                "data": bytes_to_b64(jpeg_bytes),
                                "mime_type": "image/jpeg",
                            },
                            spinner="Compressing the photo and reading cash versus credit...",
                            capture_source="image",
                        )

result = st.session_state.result
summary_lang = current_summary_language()
if result:
    attach_local_summaries(result)
    business = result.get("business_name", "Unspecified")
    date = result.get("date", "Unspecified")
    category = result.get("business_category") or st.session_state.business_category
    with st.container(border=True):
        st.header("Certificate", icon=":material/verified:")
        st.caption(f"{business} · {date}" + (f" · {category}" if category else ""))
        if result.get("capture_source") == "audio":
            st.badge("Spoken statement", icon=":material/mic:", color="blue")
        transcript = _plain(result.get("transcript"))
        if transcript:
            with st.expander("Spoken transcript", icon=":material/record_voice_over:"):
                st.write(transcript)
        with st.container(horizontal=True):
            st.metric(
                "Recorded revenue",
                result.get("total_revenue_usd", 0.0),
                border=True,
                format="dollar",
            )
            st.metric(
                "Cash received",
                result.get("total_cash_usd", 0.0),
                border=True,
                format="dollar",
            )
            st.metric(
                "Outstanding credit",
                result.get("total_credit_outstanding_usd", 0.0),
                border=True,
                format="dollar",
            )

        tx_df = pd.DataFrame(result.get("transactions") or [])
        if not tx_df.empty:
            display_df = tx_df.rename(
                columns={
                    "item": "Item",
                    "quantity": "Quantity",
                    "amount_usd": "Amount (USD)",
                    "payment_type": "Payment type",
                    "debtor": "Debtor",
                }
            )
            st.subheader("Line items", icon=":material/table:")
            st.dataframe(
                display_df,
                hide_index=True,
                column_config={
                    "Amount (USD)": st.column_config.NumberColumn(format="dollar"),
                },
            )

        summaries = {
            "English": result.get("business_health_summary") or "Summary unavailable.",
            "ChiShona": result.get("summary_shona") or "Hapana pfupiso.",
            "IsiNdebele": result.get("summary_ndebele") or "Asikho isifinyezo.",
        }
        st.subheader("Local summary", icon=":material/translate:")
        st.caption("English, ChiShona, and IsiNdebele so a trader who does not use English can still hear the day's book.")
        english_col, shona_col, ndebele_col = st.columns(3, gap="medium")
        with english_col:
            st.markdown("**English**")
            st.markdown(summaries["English"])
        with shona_col:
            st.markdown("**ChiShona**")
            st.markdown(summaries["ChiShona"])
        with ndebele_col:
            st.markdown("**IsiNdebele**")
            st.markdown(summaries["IsiNdebele"])
        st.caption(
            "AI-assisted indexing only. Totals are recalculated from extracted line items. "
            "This is not an IT audit, tax audit, or certified financial report. "
            "Pfupiso iyi haisi audit. Lesifinyezo akusona i-audit."
        )

        mix = payment_mix_df(result.get("transactions") or [])
        items = item_amount_df(result.get("transactions") or [])
        download_col, visuals_col = st.columns((1, 1.5), gap="large")
        with download_col:
            st.subheader("Export", icon=":material/picture_as_pdf:")
            st.download_button(
                label="Download PDF certificate",
                data=build_statement_pdf(result),
                file_name=statement_pdf_filename(result),
                mime="application/pdf",
                icon=":material/download:",
                type="primary",
            )
            st.caption("This statement is saved for the 7-day projection.")
        with visuals_col:
            st.subheader("This page", icon=":material/bar_chart:")
            if not mix.empty:
                st.bar_chart(
                    mix,
                    x="Payment type",
                    y="Amount",
                    horizontal=True,
                    x_label="Payment type",
                    y_label="Amount (USD)",
                )
            if not items.empty:
                st.bar_chart(
                    items.head(8),
                    x="Item",
                    y="Amount",
                    x_label="Item",
                    y_label="Amount (USD)",
                )
            if mix.empty and items.empty:
                st.caption("No transaction amounts to chart for this ledger.")

saved_ledgers = st.session_state.saved_ledgers
if saved_ledgers:
    trend = history_and_projection_df(saved_ledgers)
    recorded = trend[trend["Kind"] == "Recorded"]
    projected = trend[trend["Kind"] == "Projected"]
    week_revenue = float(projected["Revenue"].sum()) if not projected.empty else 0.0
    week_cash = float(projected["Cash"].sum()) if not projected.empty else 0.0
    next_credit = float(projected["Credit"].iloc[0]) if not projected.empty else 0.0
    revenue_history = recorded["Revenue"].tolist()
    with st.container(border=True):
        st.header("Projection", icon=":material/trending_up:")
        st.caption(
            f"{len(saved_ledgers)} saved statement(s). "
            "This is a simple trend from recorded pages, not a credit decision."
        )
        with st.container(horizontal=True):
            st.metric(
                "7-day revenue",
                week_revenue,
                border=True,
                format="dollar",
                chart_data=revenue_history + projected["Revenue"].tolist(),
                chart_type="line",
            )
            st.metric(
                "7-day cash",
                week_cash,
                border=True,
                format="dollar",
                chart_data=recorded["Cash"].tolist() + projected["Cash"].tolist(),
                chart_type="line",
            )
            st.metric(
                "Projected credit",
                next_credit,
                border=True,
                format="dollar",
                chart_data=recorded["Credit"].tolist() + projected["Credit"].tolist(),
                chart_type="line",
            )
        proj_copy = projection_local_summaries(week_revenue, week_cash, next_credit)
        st.markdown(proj_copy.get(summary_lang) or proj_copy["ChiShona"])
        if result is None:
            last_ledger = dict(saved_ledgers[-1])
            attach_local_summaries(last_ledger)
            last_local = {
                "English": last_ledger.get("business_health_summary") or "",
                "ChiShona": last_ledger.get("summary_shona") or "",
                "IsiNdebele": last_ledger.get("summary_ndebele") or "",
            }.get(summary_lang)
            if last_local:
                st.caption("Last saved ledger")
                st.markdown(last_local)
        chart_col, table_col = st.columns((1.6, 1), gap="large")
        with chart_col:
            st.line_chart(
                trend,
                x="Period",
                y=["Revenue", "Cash", "Credit"],
                x_label="Saved ledger / forecast day",
                y_label="USD",
            )
        with table_col:
            history_table = recorded.rename(
                columns={
                    "Period": "Ledger",
                    "Revenue": "Revenue (USD)",
                    "Cash": "Cash (USD)",
                    "Credit": "Credit (USD)",
                }
            ).drop(columns=["Kind"])
            st.dataframe(
                history_table,
                hide_index=True,
                column_config={
                    "Revenue (USD)": st.column_config.NumberColumn(format="dollar"),
                    "Cash (USD)": st.column_config.NumberColumn(format="dollar"),
                    "Credit (USD)": st.column_config.NumberColumn(format="dollar"),
                },
            )
