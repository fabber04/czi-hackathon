import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("GEMINI_API_KEY not found. Enter a key in the app sidebar or add it to a .env file.")
else:
    try:
        client = genai.Client(api_key=api_key)
        interaction = client.interactions.create(
            model="gemini-3.6-flash",
            input="Confirm API connection for PocketLedger hackathon project in one sentence.",
        )
        print("API connection successful.")
        print("Response:", interaction.output_text)
    except Exception as error:
        print("Error testing Gemini API:", str(error))
