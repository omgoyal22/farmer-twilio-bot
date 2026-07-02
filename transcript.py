"""
Transcript management — append and retrieve transcript entries.
"""
from models import transcripts


async def append_transcript(call_sid: str, speaker: str, text: str, entry_type: str):
    """
    Append a transcript entry for the given call_sid.
    Creates the transcript list if it doesn't exist yet.
    """
    if call_sid not in transcripts:
        transcripts[call_sid] = []

    transcripts[call_sid].append({
        "speaker": speaker,
        "text": text,
        "type": entry_type
    })


def get_transcript(call_sid: str):
    """
    Retrieve the full transcript for a call_sid.
    Returns an empty list if no transcript exists.
    """
    return transcripts.get(call_sid, [])


async def save_transcript_to_file(call_sid: str):
    """
    Saves the transcript of a call to a JSON file.
    """
    import json
    import os
    
    transcript = get_transcript(call_sid)
    if not transcript:
        return
        
    os.makedirs("saved_transcripts", exist_ok=True)
    file_path = os.path.join("saved_transcripts", f"transcript_{call_sid}.json")
    
    with open(file_path, "w") as f:
        json.dump(transcript, f, indent=4)
        
    print(f"Transcript saved to {file_path}")
