import os
from dotenv import load_dotenv
load_dotenv()

gemini_key = os.getenv("GEMINI_API_KEY")

from google import genai
from google.genai import types

gclient = genai.Client(api_key=gemini_key)

response = gclient.models.generate_content(
    model="gemini-3.6-flash",
    contents="Hello from Jarvis! Answer in 1 short sentence."
)
print("SUCCESS with gemini-3.6-flash:", response.text)
