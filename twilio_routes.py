"""
Twilio HTTP routes — TwiML endpoints and call initiation.
"""
from fastapi import APIRouter, Request, Response
from config import (
    DOMAIN, WS_URL, WELCOME_GREETING,
    TWILIO_PHONE_NUMBER, twilio_client
)
from models import (
    FarmerCallRequest, CallResponse,
    call_metadata, outbound_messages, transcripts, sessions
)
from gemini_handler import get_gemini_model
import re

router = APIRouter()

_ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def _clean_error_message(message: str) -> str:
    """Twilio exceptions can include ANSI color codes; strip for API clients."""
    if not message:
        return message
    return _ANSI_ESCAPE_RE.sub("", message).strip()


# ========================
# POST /twiml — Inbound TwiML
# ========================

@router.post("/twiml")
async def twiml_endpoint(request: Request):
    """
    Returns TwiML XML for Twilio to connect the call
    to the ConversationRelay WebSocket (inbound calls).
    """
    xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <ConversationRelay
            url="{WS_URL}"
            welcomeGreeting="{WELCOME_GREETING.strip()}"
            language="hi-IN"
            ttsProvider="ElevenLabs"
            voice="RDWdsTU6N02BFftbIEAp"
            endSilenceTimeoutMs="500"
            startSilenceTimeoutMs="300"
            speechTimeout="1000"
            enhanced="true" />
    </Connect>
</Response>"""
    return Response(content=xml_response, media_type="text/xml")


# ========================
# GET /twiml — Inbound TwiML (GET variant)
# ========================

@router.get("/twiml")
async def twiml_endpoint_get(request: Request):
    """GET variant of the TwiML endpoint."""
    return await twiml_endpoint(request)


# ========================
# POST /twiml-outbound — Outbound TwiML
# ========================

@router.post("/twiml-outbound")
async def twiml_outbound(request: Request):
    """
    Returns TwiML XML for outbound calls.
    Reads the greeting message from in-memory store using CallSid.
    """
    # Parse form data from Twilio's POST
    form_data = await request.form()
    call_sid = form_data.get("CallSid") or request.query_params.get("CallSid")
    print(f"TwiML for CallSid: {call_sid}")

    # Fetch stored greeting or use default
    message = outbound_messages.get(
        call_sid,
        "नमस्कार किसान भाई। मैं वाणी, आपकी किसान सेवा सलाहकार। मैं आपको सरकारी योजनाओं की जानकारी दे सकती हूँ और आपकी शिकायतें दर्ज कर सकती हूँ। बताइए, क्या आप शिकायत दर्ज करना चाहते हैं, या योजनाओं के बारे में जानना चाहते हैं?"
    )

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <ConversationRelay
            url="{WS_URL}"
            welcomeGreeting="{message}"
            language="hi-IN"
            ttsProvider="ElevenLabs"
            voice="RDWdsTU6N02BFftbIEAp"
            endSilenceTimeoutMs="500"
            startSilenceTimeoutMs="300"
            speechTimeout="1000"
            enhanced="true" />
    </Connect>
</Response>"""
    return Response(content=xml, media_type="text/xml")


# ========================
# GET /twiml-outbound — Outbound TwiML (GET variant)
# ========================

@router.get("/twiml-outbound")
async def twiml_outbound_get(request: Request):
    """GET variant of the outbound TwiML endpoint."""
    return await twiml_outbound(request)


# ========================
# POST /initiate-call — Start an outbound call
# ========================

@router.post("/initiate-call", response_model=CallResponse)
async def initiate_call(payload: FarmerCallRequest):
    """
    Initiates an outbound Twilio call to the farmer.
    Stores metadata, greeting, and initial transcript.
    """
    try:
        # Initialize Gemini model for this farmer
        model = get_gemini_model(payload.farmer_name)

        print("djklashfk;asjhfpkahjf;ksah;fkh")

        # Make Twilio call
        call = twilio_client.calls.create(
            to=payload.to,
            from_=TWILIO_PHONE_NUMBER,
            url=f"{DOMAIN}/twiml-outbound",
            record=True
        )

        call_sid = call.sid  # Twilio's real SID (starts with CA...)
        print(f"Call initiated to {payload.to} | Twilio SID: {call_sid}")

        # Store greeting message
        greeting_text = f"नमस्कार {payload.farmer_name} जी। मैं वाणी, आपकी किसान सेवा सलाहकार। मैं आपको सरकारी योजनाओं की जानकारी दे सकती हूँ और आपकी शिकायतें दर्ज कर सकती हूँ। बताइए, क्या आप शिकायत दर्ज करना चाहते हैं, या योजनाओं के बारे में जानना चाहते हैं?"
        outbound_messages[call_sid] = greeting_text

        # Store metadata for this call
        call_metadata[call_sid] = {
            "farmer_name": payload.farmer_name
        }

        # Store the Gemini model (will create chat session when WS connects)
        sessions[call_sid] = {"model": model, "chat": None}

        # Initialize transcript with greeting
        transcripts[call_sid] = [
            {
                "speaker": "bot",
                "text": greeting_text,
                "type": "response"
            },
            {
                "speaker": "system",
                "text": "Call initiated",
                "type": "call_start"
            }
        ]

        print(f"Call Metadata: {call_metadata[call_sid]}")

        return CallResponse(
            status="success",
            call_sid=call_sid,
            to=payload.to,
            farmer_name=payload.farmer_name
        )

    except Exception as e:
        print(f"Call initiation error: {e}")
        return CallResponse(
            status="error",
            message=_clean_error_message(str(e))
        )


# ========================
# GET /transcript/{call_sid} — Retrieve transcript
# ========================

@router.get("/transcript/{call_sid}")
async def get_transcript_endpoint(call_sid: str):
    """Retrieve the transcript for a specific call."""
    from transcript import get_transcript
    transcript = get_transcript(call_sid)
    return {
        "call_sid": call_sid,
        "transcript": transcript,
        "count": len(transcript)
    }


# ========================
# GET /calls — List all active calls
# ========================

@router.get("/calls")
async def list_calls():
    """List all tracked calls with their metadata."""
    return {
        "calls": [
            {
                "call_sid": sid,
                "farmer_name": meta.get("farmer_name"),
                "transcript_count": len(transcripts.get(sid, []))
            }
            for sid, meta in call_metadata.items()
        ]
    }
