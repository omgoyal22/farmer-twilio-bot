"""
main.py — FastAPI Application Entry Point

Twilio + Google Gemini AI Recruiter Bot (Jessi)

Run with:
    python main.py

Or:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from twilio_routes import router as twilio_router
from ws_handler import websocket_handler
from config import HOST, PORT

# ========================
# FastAPI App
# ========================

app = FastAPI(
    title="Sunita AI Farmer Scheme Bot",
    description="Twilio + Google Gemini powered AI farmer scheme voice bot",
    version="1.0.0"
)

# CORS — allow all origins (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================
# Mount HTTP Routes
# ========================

# All Twilio routes: /twiml, /twiml-outbound, /initiate-call, /transcript/{call_sid}, /calls
app.include_router(twilio_router)

# ========================
# WebSocket Route
# ========================

@app.websocket("/ws/")
async def ws_endpoint(websocket: WebSocket):
    """Twilio ConversationRelay WebSocket endpoint."""
    await websocket_handler(websocket)


# Also accept without trailing slash
@app.websocket("/ws")
async def ws_endpoint_no_slash(websocket: WebSocket):
    """Twilio ConversationRelay WebSocket endpoint (no trailing slash)."""
    await websocket_handler(websocket)


# ========================
# Health Check
# ========================

@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "running",
        "service": "Sunita AI Farmer Scheme Bot",
        "version": "1.0.0",
        "endpoints": {
            "POST /initiate-call": "Start an outbound call to a farmer",
            "POST /twiml": "TwiML for inbound calls",
            "POST /twiml-outbound": "TwiML for outbound calls",
            "GET /calls": "List all tracked calls",
            "GET /transcript/{call_sid}": "Get transcript for a call",
            "WebSocket /ws/": "Twilio ConversationRelay WebSocket"
        }
    }


# ========================
# Run Server
# ========================

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("Sunita AI Farmer Scheme Bot — Starting...")
    print(f"Server: http://{HOST}:{PORT}")
    print(f"API Docs: http://{HOST}:{PORT}/docs")
    print("=" * 50)
    uvicorn.run(
        "main:app",
        host=HOST,
        port=int(PORT),
        reload=True,
        ws_ping_interval=20,
        ws_ping_timeout=20
    )
