"""
WebSocket handler for Twilio ConversationRelay.

Twilio sends candidate speech as JSON via WebSocket.
We process it with Gemini and send back AI response text.

ConversationRelay Protocol:
- Twilio sends: {"type": "setup", "callSid": "CA...", ...} on connect
- Twilio sends: {"type": "prompt", "voicePrompt": "candidate text"} for speech
- We respond:   {"type": "text", "token": "response text", "last": true/false}
"""
import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from models import sessions, call_metadata
from gemini_handler import gemini_response, get_gemini_model
from transcript import append_transcript, save_transcript_to_file


async def websocket_handler(websocket: WebSocket):
    """
    Handle a single Twilio ConversationRelay WebSocket connection.
    Converted directly from the original Django Channels consumer.
    """
    await websocket.accept()
    call_sid = None
    chat_session = None
    is_generating = False  # Flag to prevent re-entry/race conditions

    print("✅ WebSocket connected")

    try:
        while True:
            # Receive message from Twilio
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                print("Invalid JSON message received.")
                continue

            msg_type = data.get("type", "")

            # ========================
            # SETUP (Initial handshake)
            # ========================
            if msg_type == "setup":
                call_sid = data.get("callSid") or data.get("call_sid") or data.get("callSidFromTwilio")
                if not call_sid:
                    print("⚠️ setup message without callSid")
                    continue
                
                print(f"WebSocket setup | CallSid: {call_sid}")

                # Retrieve or initialize metadata
                meta = call_metadata.get(call_sid, {})
                
                # Fallback to data from setup message if no pre-stored metadata
                if not meta:
                    meta = {
                        "farmer_name": data.get("farmer_name", "किसान"),
                    }

                try:
                    # Check if we already have a pre-stored model inside sessions
                    if call_sid in sessions and sessions[call_sid].get("model"):
                        model = sessions[call_sid]["model"]
                    else:
                        model = get_gemini_model(**meta)
                        
                    chat_session = model.start_chat(history=[])
                    sessions[call_sid] = {"model": model, "chat": chat_session}
                    
                    await append_transcript(call_sid, "system", "Call connected", "call_start")
                    print(f"✅ Gemini session started for {meta.get('farmer_name')} ({call_sid})")

                except Exception as e:
                    print(f"Model initialization error for {call_sid}: {e}")
                    await websocket.close()
                    return

            # ========================
            # PROMPT (User speech transcript)
            # ========================
            elif msg_type == "prompt":
                if not chat_session or is_generating:
                    continue

                user_prompt = (
                    data.get("voicePrompt", "") or
                    data.get("transcript", "") or
                    data.get("text", "")
                ).strip()

                if not user_prompt:
                    continue

                # Save candidate speech asynchronously
                asyncio.create_task(
                    append_transcript(call_sid, "candidate", user_prompt, "prompt")
                )

                print(f"PROMPT (user): '{user_prompt}'")

                is_generating = True
                try:
                    await gemini_response(
                        chat_session,
                        user_prompt,
                        websocket=websocket,
                        call_sid=call_sid
                    )
                finally:
                    is_generating = False

            # ========================
            # INTERRUPT
            # ========================
            elif msg_type == "interrupt":
                print(f"[{call_sid}] Candidate interrupted")
                await append_transcript(call_sid, "system", "Candidate interrupted", "interrupt")

            # ========================
            # DTMF
            # ========================
            elif msg_type == "dtmf":
                digit = data.get("digit", "")
                print(f"[{call_sid}] DTMF: {digit}")

            # ========================
            # ERROR
            # ========================
            elif msg_type == "error":
                error_desc = data.get("description", "Unknown error")
                print(f"[{call_sid}] Twilio error: {error_desc}")
                await append_transcript(call_sid, "system", f"Error: {error_desc}", "error")

            else:
                print(f"Unhandled message type: {msg_type}")

    except WebSocketDisconnect:
        if call_sid:
            if call_sid in sessions:
                asyncio.create_task(
                    append_transcript(call_sid, "system", "Call ended", "call_end")
                )
                sessions.pop(call_sid, None)
                # Save the transcript to a file automatically
                asyncio.create_task(save_transcript_to_file(call_sid))
        print(f"WebSocket disconnected: {call_sid}")

    except Exception as e:
        print(f"WebSocket error: {e}")
        if call_sid:
            await asyncio.create_task(
                append_transcript(call_sid, "system", f"Error: {str(e)}", "error")
            )

