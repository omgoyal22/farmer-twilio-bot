"""
Configuration module — loads environment variables and initializes Twilio client.
"""
import os
import re
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv(override=True)

# ============ Google Gemini ============
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()

# ============ Twilio ============
TWILIO_ACCOUNT_SID=os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN=os.getenv("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_PHONE_NUMBER=""


# ============ Domain / URLs ============
DOMAIN = os.getenv("DOMAIN", "")
DOMAIN_CLEAN = DOMAIN.replace("https://", "").replace("http://", "")
WS_URL = f"wss://{DOMAIN_CLEAN}/ws/"

# ============ Server ============
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# ============ Twilio Client ============
def _looks_like_twilio_sid(value: str) -> bool:
    return bool(re.fullmatch(r"AC[a-fA-F0-9]{32}", value or ""))


def _mask(value: str, keep: int = 6) -> str:
    if not value:
        return ""
    if len(value) <= keep:
        return "*" * len(value)
    return value[:keep] + ("*" * (len(value) - keep))


if not _looks_like_twilio_sid(TWILIO_ACCOUNT_SID):
    raise ValueError(
        "Invalid TWILIO_ACCOUNT_SID in .env. Expected format like 'AC' + 32 hex chars."
    )

if not TWILIO_AUTH_TOKEN:
    raise ValueError("TWILIO_AUTH_TOKEN not set in .env.")

if not TWILIO_PHONE_NUMBER:
    raise ValueError("TWILIO_PHONE_NUMBER not set in .env (must be a Twilio-owned number).")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ============ Welcome Greeting ============
WELCOME_GREETING = "नमस्कार किसान भाई। मैं वाणी, आपकी किसान सेवा सलाहकार। मैं आपको सरकारी योजनाओं की जानकारी दे सकती हूँ और आपकी शिकायतें दर्ज कर सकती हूँ। बताइए, क्या आप शिकायत दर्ज करना चाहते हैं, या योजनाओं के बारे में जानना चाहते हैं?"

print(f"[OK] Config loaded | Domain: {DOMAIN}")
print(f"WS URL: {WS_URL}")
print(f"[OK] Twilio SID: {_mask(TWILIO_ACCOUNT_SID)} | From: {TWILIO_PHONE_NUMBER}")
