"""
Gemini AI Handler — System prompt, model initialization, response generation.
Converted from the original Django code to work with FastAPI.
"""
import os
import re
import json
import asyncio
import google.generativeai as genai
from config import GOOGLE_API_KEY
from models import call_metadata, conversation_context
from transcript import append_transcript


# ========================
# System Prompt Builder
# ========================

def information_extract(farmer_name):
    """Build the structured system prompt for Gemini for farmers."""

    SYSTEM_PROMPT = f"""
            You are **Vani (वाणी)**, an AI **Kisan Seva Salahakar** (किसान सेवा सलाहकार) for the Government.
            You conduct conversational calls with farmers in **Hindi**.
            Your style should be polite, helpful, empathetic, and natural.
            Speak **one statement/question at a time**, and wait for the farmer to respond.
            Respond in Hindi written in Devanagari script. 
            Do NOT mention that you are an AI or bot, just speak naturally as Vani.

            =========================
            **OBJECTIVE**

            Guide the farmer through a menu: complaint registration or scheme information.

            =========================
            **Context**
            - Farmer Name: {farmer_name}

            =========================
            **CONVERSATION FLOW & RULES**

            ### 1. Introduction
            - **Start exactly with:** "नमस्कार किसान भाई। मैं वाणी, आपकी किसान सेवा सलाहकार। मैं आपको सरकारी योजनाओं की जानकारी दे सकती हूँ और आपकी शिकायतें दर्ज कर सकती हूँ। बताइए, क्या आप शिकायत दर्ज करना चाहते हैं, या योजनाओं के बारे में जानना चाहते हैं?"
            - Wait for the farmer's response.

            ### 2. Handling Response
            - **If Complaint (शिकायत):**
              - Ask for details of the complaint.
              - Once they tell the complaint, acknowledge it: "आपकी शिकायत दर्ज कर ली गई है। हमारी टीम आपकी प्रॉब्लम देखकर आपको जल्दी समाधान देगी।"
              - Then ask if they want to know about schemes.

            - **If Schemes (योजना):**
              - Ask: "मेरे पास अभी 3 मुख्य योजनाएं हैं: पहली खेती और खाद के लिए, दूसरी बच्चों की पढ़ाई के लिए, और तीसरी पेंशन के लिए। बताइए आप किस योजना में इंटरेस्टेड हैं?"
              - Wait for response.

            ### 3. Gathering Details before Scheme Explanation
            - Once they choose a scheme, say: "योजना बताने से पहले, क्या मैं जान सकती हूँ कि आपके परिवार में कितने सदस्य हैं? और खेती में कोई दिक्कत तो नहीं आ रही है?"
            - Wait for response.
            - If they mention a problem in farming, say: "आपकी यह समस्या शिकायत के तौर पर दर्ज कर ली गई है। हमारी टीम आपकी प्रॉब्लम देखकर आपको जल्दी समाधान देगी।"
            - Then ask: "योजना के लिए, मैं आपसे यह जानना चाहती हूँ कि सालाना खेती से आपकी क्या आय हो जाती है?"
            - Wait for response.
            - **If farmer hesitates or refuses to share income:** Reassure them gently: "कोई बात नहीं, मैं समझ सकती हूँ। बस एक अंदाज़ा बता दीजिए जैसे 2 लाख से कम या ज़्यादा, ताकि मैं सही योजना बता सकूँ?"

            ### 4. Scheme Eligibility and Explanation based on Income
            - **Less than 2 Lakh (< 2 Lakh):**
              "आप तीनों योजनाओं के लिए योग्य हैं। 1. खाद पर 20% छूट और 6000 रुपये महीना। 2. बच्चों की 100% फीस माफ़। 3. पेंशन योजना का भी लाभ।"
            - **Between 2 to 5 Lakh:**
              "आप पहली दो योजनाओं के लिए योग्य हैं। आपको खाद पर 20% छूट मिलेगी और बच्चों की फीस माफ़ हो जाएगी। पेंशन योजना का लाभ नहीं मिलेगा।"
            - **Above 5 Lakh (> 5 Lakh):**
              "आप सिर्फ एक ही योजना के लिए योग्य हैं। आपको खाद पर 20% छूट मिलेगी।"

            ### 5. Wrap-Up
            - "क्या आप कुछ और जानना चाहते हैं?"
            - If no: "धन्यवाद। आपका दिन शुभ हो।"

            =========================
            **VALIDATION RULES**
            - Keep the conversation strictly around these schemes and complaints.
            - Speak only in Hindi.
            - ALWAYS speak in complete sentences ending with proper punctuation (पूर्ण विराम । or ?). NEVER leave sentences incomplete or unfinished.

            """
    return SYSTEM_PROMPT


# ========================
# Gemini Model Initialization
# ========================

def get_farmer_info(farmer_name):
    """Build farmer info dict."""
    return {
        "farmer_name": farmer_name
    }


def get_gemini_model(farmer_name):
    """Initialize Gemini model dynamically with farmer info."""
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not set in .env!")

    genai.configure(api_key=GOOGLE_API_KEY)

    generation_config = genai.types.GenerationConfig(
        max_output_tokens=600,
        temperature=0.7,
        top_p=0.9,
        top_k=64,
        candidate_count=1
    )

    farmer_info = get_farmer_info(farmer_name)

    model = genai.GenerativeModel(
        model_name=os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip(),
        system_instruction=information_extract(**farmer_info),
        generation_config=generation_config
    )

    return model


# ========================
# Text Cleaning
# ========================

def clean_response_text(text):
    """Clean markdown/special chars for voice output."""
    if not text:
        return text
    text = re.sub(r'[*_~`#]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ========================
# Candidate Response Analysis
# ========================

def analyze_farmer_response(user_prompt, call_sid):
    """
    Detect farmer intent patterns and enhance the prompt if needed.
    """
    user_lower = user_prompt.lower().strip()

    # Init conversation context
    if call_sid not in conversation_context:
        conversation_context[call_sid] = {
            "stage": "introduction",
            "unexpected_responses": set(),
            "farmer_concerns": set()
        }

    context = conversation_context[call_sid]

    patterns = {
        "confusion": ["kaun", "kya", "samajh nahi"],
        "income": ["kamata", "rupye", "hazar", "lakh", "salana"],
        "disinterest": ["nahi", "chahiye", "rakho"]
    }

    detected = set()
    for category, keywords in patterns.items():
        if any(keyword in user_lower for keyword in keywords):
            detected.add(category)

    # No special patterns → return original prompt
    if not detected:
        return user_prompt

    # Store concerns
    context["unexpected_responses"].update(detected)
    context["farmer_concerns"].update(detected)

    # Pull metadata
    meta = call_metadata.get(call_sid, {})
    farmer_name = meta.get("farmer_name", "किसान")

    enhanced_prompt = f"{user_prompt}\n\n(निर्देश: किसान को विनम्रता से 1 या 2 पूरे वाक्यों में उत्तर दें। वाक्य हमेशा पूर्ण विराम पर समाप्त करें।)"

    return enhanced_prompt


# ========================
# Gemini Response (Async)
# ========================

async def gemini_response(chat_session, user_prompt, websocket=None, call_sid=None):
    """
    Send user prompt to Gemini, get response, send back via WebSocket.
    Handles timeouts and errors gracefully.
    """
    try:
        # Removed instant acknowledgment ("Okay...") to prevent repetitive behavior

        # Enhance prompt if patterns detected
        enhanced_prompt = user_prompt
        if call_sid:
            enhanced_prompt = analyze_farmer_response(user_prompt, call_sid)

        # Truncate to 500 chars max
        enhanced_prompt = enhanced_prompt[:500]

        # Call Gemini with timeout
        response = await asyncio.wait_for(
            chat_session.send_message_async(enhanced_prompt),
            timeout=5.0
        )

        cleaned_response = clean_response_text(response.text)

        # Send response via WebSocket
        if websocket:
            await websocket.send_json({
                "type": "text",
                "token": cleaned_response,
                "last": True
            })

        # Save transcript asynchronously (non-blocking)
        if call_sid:
            asyncio.create_task(
                append_transcript(call_sid, "bot", cleaned_response, "response")
            )
            print(f"RESPONSE (bot): '{cleaned_response}'")

        return cleaned_response

    except asyncio.TimeoutError:
        fallback = "Could you repeat that?"
        if websocket:
            await websocket.send_json({
                "type": "text",
                "token": fallback,
                "last": True
            })
        return fallback

    except Exception as e:
        print(f"Gemini API error: {e}")
        fallback = "Could you repeat that?"
        if websocket:
            await websocket.send_json({
                "type": "text",
                "token": fallback,
                "last": True
            })
        return fallback
