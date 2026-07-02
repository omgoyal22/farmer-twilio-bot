"""
Pydantic models for API request/response + in-memory data stores.
"""
from pydantic import BaseModel
from typing import Optional, Dict, List, Any


# ========================
# Pydantic Models
# ========================

class FarmerCallRequest(BaseModel):
    """Request body for POST /initiate-call"""
    to: str  # Phone number to call (e.g., "+919876543210")
    farmer_name: str


class CallResponse(BaseModel):
    """Response from POST /initiate-call"""
    status: str
    call_sid: Optional[str] = None
    to: Optional[str] = None
    farmer_name: Optional[str] = None
    message: Optional[str] = None


class TranscriptEntry(BaseModel):
    """Single transcript entry"""
    speaker: str  # "bot", "candidate", "system"
    text: str
    type: str  # "response", "speech", "call_start", "call_end"


# ========================
# In-Memory Data Stores
# ========================

# Gemini chat sessions per call_sid
sessions: Dict[str, Any] = {}

# Candidate metadata per call_sid
call_metadata: Dict[str, Dict[str, str]] = {}

# Outbound greeting messages per call_sid
outbound_messages: Dict[str, str] = {}

# Transcripts per call_sid
transcripts: Dict[str, List[Dict[str, str]]] = {}

# Conversation context for response analysis per call_sid
conversation_context: Dict[str, Dict[str, Any]] = {}
