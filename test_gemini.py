"""Independent Gemini API test.

Set GEMINI_API_KEY as a user environment variable, or put it in a local .env file.
Run from the project folder with the virtual environment active:

    python test_gemini.py
"""

from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client()
interaction = client.interactions.create(
    model="gemini-3.6-flash",
    input="Explain AI governance in one simple sentence.",
)
print(interaction.output_text)
