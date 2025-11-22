import streamlit as st
import requests
import uuid
from datetime import datetime
import json
import re

# Page configuration
st.set_page_config(
    page_title="Travel Assistant AI",
    page_icon="🛩️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        padding: 1rem 0;
        font-weight: bold;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .user-message {
        background-color: #1c669c;
        border-left: 4px solid #1E88E5;
    }
    .assistant-message {
        background-color: #2c7524;
        border-left: 4px solid #43A047;
    }
    .assistant-message a {
        color: #90CAF9;
        text-decoration: underline;
    }
    .assistant-message a:hover {
        color: #64B5F6;
    }
    .success-box {
        padding: 1rem;
        background-color: #207a27;
        border-radius: 0.5rem;
        border-left: 4px solid #43A047;
        margin: 1rem 0;
    }
    .stButton>button {
        width: 100%;
        background-color: #1E88E5;
        color: white;
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #1565C0;
    }
</style>
""", unsafe_allow_html=True)

# Backend API configuration
import os
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    
if "show_debug" not in st.session_state:
    st.session_state.show_debug = False

def call_backend(message: str) -> dict:
    """Call the backend API with user message."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/chat",
            json={
                "session_id": st.session_state.session_id,
                "message": message
            },
            timeout=45  # Increased timeout for complex queries
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {
            "error": "Cannot connect to backend. Make sure the backend is running on port 8000."
        }
    except requests.exceptions.Timeout:
        return {
            "error": "Request timed out. The query might be too complex. Please try a more specific location or try again."
        }
    except Exception as e:
        return {
            "error": f"An error occurred: {str(e)}"
        }

def check_backend_health() -> bool:
    """Check if backend is running."""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def markdown_to_html(text: str) -> str:
    """Convert Markdown links and formatting to HTML."""
    # Convert bold **text** to <b>text</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # Convert italic _text_ to <i>text</i>
    text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
    # Convert Markdown links [text](url) to HTML <a> tags
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" target="_blank">\1</a>', text)
    # Convert newlines to <br> tags
    text = text.replace('\n', '<br>')
    return text

def display_message(role: str, content: str, metadata: dict = None):
    """Display a chat message with proper formatting."""
    if role == "user":
        st.markdown(f'<div class="chat-message user-message"><b>You:</b><br>{content}</div>', unsafe_allow_html=True)
    else:
        # Convert Markdown to HTML for proper link rendering
        html_content = markdown_to_html(content)
        message_container = f"""
        <div class="chat-message assistant-message">
            <b>🤖 Travel Assistant:</b><br><br>
            {html_content}
        </div>
        """
        st.markdown(message_container, unsafe_allow_html=True)
        
        # Show debug info if enabled
        if metadata and st.session_state.show_debug:
            with st.expander("🔍 Debug Information"):
                if "extracted_location" in metadata and metadata["extracted_location"]:
                    loc = metadata["extracted_location"]
                    st.write(f"**Location:** {loc.get('name')} ({loc.get('lat')}, {loc.get('lon')})")
                
                if "intent" in metadata:
                    st.write(f"**Intent:** {metadata['intent']}")
                
                if "steps" in metadata:
                    st.write("**Processing Steps:**")
                    for step in metadata["steps"]:
                        status_icon = "✅" if step["status"] == "success" else "❌"
                        st.write(f"{status_icon} {step['step_name']}: {step['details']}")
                
                if "data" in metadata:
                    st.write("**Data:**")
                    st.json(metadata["data"])

# Header
st.markdown('<div class="main-header">✈️ AI Travel Assistant</div>', unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>Your intelligent companion for travel planning and weather information</p>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Backend status
    backend_status = check_backend_health()
    if backend_status:
        st.markdown('<div class="success-box">✅ Backend Connected</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="info-box">⚠️ Backend Disconnected<br><small>Run: <code>uvicorn app.main:app --reload</code> in backend folder</small></div>', unsafe_allow_html=True)
    
    st.divider()
    
    # Debug toggle
    st.session_state.show_debug = st.checkbox("Show Debug Info", value=st.session_state.show_debug)
    
    st.divider()
    
    # Session info
    st.subheader("📊 Session Info")
    st.write(f"**Session ID:** `{st.session_state.session_id[:8]}...`")
    st.write(f"**Messages:** {len(st.session_state.chat_history)}")
    
    if st.button("🔄 New Session"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.chat_history = []
        st.rerun()
    
    st.divider()
    
    # Example queries
    st.subheader("💡 Try These Examples")
    
    example_queries = [
        "I'm going to Bangalore, let's plan my trip.",
        "What is the weather in Mumbai?",
        "I'm going to Delhi, what's the temperature and what places can I visit?",
        "Show me places to visit in Paris",
        "What's the weather like in Tokyo?"
    ]
    
    for query in example_queries:
        if st.button(query, key=f"example_{query[:20]}", use_container_width=True):
            st.session_state.pending_query = query
            st.rerun()

# Main chat interface
if not backend_status:
    st.warning("⚠️ Backend is not running. Please start the backend server first.")
    st.code("cd backend && uvicorn app.main:app --reload", language="bash")
else:
    # Display welcome message if no chat history
    if len(st.session_state.chat_history) == 0:
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        st.markdown("""
        ### 👋 Welcome to AI Travel Assistant!
        
        I can help you with:
        - 🌤️ **Weather Information** - Get current weather for any city
        - 📍 **Places to Visit** - Discover tourist attractions and landmarks
        - 🗺️ **Trip Planning** - Get both weather and places information
        
        Just type naturally, like:
        - "What's the weather in Bangalore?"
        - "I'm going to Mumbai, show me places to visit"
        - "Plan my trip to Paris"
        """)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            display_message(
                role=message["role"],
                content=message["content"],
                metadata=message.get("metadata")
            )
    
    # Chat input
    st.divider()
    
    # Handle pending query from example buttons
    if hasattr(st.session_state, 'pending_query'):
        user_input = st.session_state.pending_query
        del st.session_state.pending_query
    else:
        user_input = st.chat_input("Ask me about weather or places to visit...")
    
    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        # Show loading spinner with better message
        with st.spinner("🔍 Searching for the best places and weather information..."):
            # Call backend
            response = call_backend(user_input)
        
        # Handle response
        if "error" in response:
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"❌ {response['error']}",
                "timestamp": datetime.now().isoformat()
            })
        else:
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response.get("message", "I couldn't process your request."),
                "metadata": response,
                "timestamp": datetime.now().isoformat()
            })
        
        # Rerun to update UI
        st.rerun()

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #999; padding: 1rem;'>
    <small>Powered by FastAPI, Mistral AI, Open-Meteo & Overpass API | Made with ❤️ using Streamlit</small>
</div>
""", unsafe_allow_html=True)