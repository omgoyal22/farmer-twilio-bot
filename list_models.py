import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv(override=True)
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("ERROR: GOOGLE_API_KEY is not set in .env")
    exit(1)

genai.configure(api_key=api_key)

print("Attempting to list models with your API key...")
try:
    models = genai.list_models()
    print("\nAvailable models for your API key:")
    for model in models:
        if "generateContent" in model.supported_generation_methods:
            print(f"- {model.name} ({model.display_name})")
except Exception as e:
    print(f"\nFailed to list models: {e}")
