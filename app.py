import os

import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL_NAME = "gemini-3.6-flash"

st.set_page_config(
    page_title="Hack for Humanity Starter",
    page_icon=":material/favorite:",
    layout="centered",
)

st.title("Hack for Humanity — Gemini Starter")
st.caption(
    "Collect a human problem, send it to the Gemini API, and show a structured response."
)

default_key = os.environ.get("GEMINI_API_KEY", "")
api_key = st.sidebar.text_input(
    "Gemini API key",
    value=default_key,
    type="password",
    help="Paste a key from Google AI Studio. Never commit this key to GitHub.",
)
st.sidebar.markdown(
    "[Get an API key](https://aistudio.google.com/) · use Dashboard → API Keys"
)

problem = st.text_area(
    "Describe the human problem you want help thinking through",
    height=160,
    placeholder="Who is affected, what is happening, and where it happens.",
)

st.info(
    "This prototype can make mistakes. Treat Gemini output as a starting point, "
    "not as medical, legal, or official advice."
)

if st.button("Ask Gemini", type="primary"):
    if not api_key:
        st.error("Please enter your Gemini API key.")
    elif not problem.strip():
        st.error("Please describe the problem.")
    else:
        client = genai.Client(api_key=api_key)
        prompt = f"""
You are helping a hackathon team understand a human problem.

Problem:
{problem}

Return:
1. Who is affected
2. Why the problem matters
3. Three possible solution directions
4. Important risks or safeguards
"""
        with st.spinner("Gemini is working..."):
            try:
                interaction = client.interactions.create(
                    model=MODEL_NAME,
                    input=prompt,
                )
                st.subheader("Gemini response")
                st.write(interaction.output_text)
            except Exception as error:
                st.error(
                    "Gemini is temporarily unavailable. "
                    "Please wait a moment and try again."
                )
                st.caption(str(error))
