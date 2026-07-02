import streamlit as st
import requests
import time

# FastAPI Backend URL
API_URL = "http://localhost:8000"

st.set_page_config(page_title="Vani AI Farmer Scheme Bot - Dashboard", layout="wide")

if 'active_call_sid' not in st.session_state:
    st.session_state.active_call_sid = None

st.title("🌾 Vani AI Farmer Scheme Dashboard")
st.markdown("Use this dashboard to initiate a call to a farmer using the Twilio + Gemini FastAPI backend.")

st.sidebar.header("Backend Connection")
api_base = st.sidebar.text_input("FastAPI Base URL", value=API_URL)

st.header("👤 Farmer Details")

col1, col2 = st.columns(2)

with col1:
    farmer_name = st.text_input("Farmer Name", value="राम कुमार")
    phone_number = st.text_input("Phone Number (with country code)", value="+91")

st.markdown("---")

col_btn, col_stop = st.columns(2)

with col_btn:
    if st.button("📞 Initiate Call", type="primary", use_container_width=True):
        with st.spinner("Connecting to backend & Twilio..."):
            payload = {
                "to": phone_number,
                "farmer_name": farmer_name
            }
            
            try:
                response = requests.post(f"{api_base}/initiate-call", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        st.session_state.active_call_sid = data.get('call_sid')
                        st.success(f"✅ Call Initiated Successfully! Twilio SID: {st.session_state.active_call_sid}")
                    else:
                        st.error(f"❌ Failed: {data.get('message')}")
                else:
                    st.error(f"Backend Error: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Could not connect to FastAPI backend: {str(e)}")

with col_stop:
    if st.session_state.active_call_sid:
        if st.button("🛑 Stop Live Transcript", use_container_width=True):
            st.session_state.active_call_sid = None
            st.rerun()

st.markdown("---")

if st.session_state.active_call_sid:
    st.subheader(f"🗣️ Live Transcript")
    
    # Fetch transcript
    try:
        resp = requests.get(f"{api_base}/transcript/{st.session_state.active_call_sid}")
        if resp.status_code == 200:
            transcript = resp.json().get("transcript", [])
            
            md_text = ""
            for msg in transcript:
                if msg['speaker'] == 'bot':
                    md_text += f"**🤖 वाणी (Vani):** {msg['text']}\n\n"
                elif msg['speaker'] == 'user':
                    md_text += f"**🌾 किसान:** {msg['text']}\n\n"
                else:
                    md_text += f"*{msg['text']}*\n\n"
            
            st.markdown(md_text)
    except Exception as e:
        st.warning(f"Could not fetch transcript: {str(e)}")
        
    # Polling delay
    time.sleep(2)
    st.rerun()

else:
    st.subheader("📋 Active Calls Tracked by Backend")
    if st.button("Refresh Active Calls"):
        try:
            response = requests.get(f"{api_base}/calls")
            if response.status_code == 200:
                calls = response.json().get("calls", [])
                if calls:
                    st.table(calls)
                else:
                    st.info("No active calls tracked.")
            else:
                st.error("Failed to fetch active calls.")
        except Exception as e:
            st.error(f"Could not reach backend: {str(e)}")
