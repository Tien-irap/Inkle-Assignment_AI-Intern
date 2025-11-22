# Inkle-Assignment_AI-Intern
Building a multi-agent tourism system with LangGraph-inspired state management

## 🌐 Live Demo

**Try it now!**
- **Frontend**: https://inkle-assignment-ai-intern-frontend.onrender.com
- **Backend API**: https://inkle-assignment-ai-intern-qj70.onrender.com
- **API Docs**: https://inkle-assignment-ai-intern-qj70.onrender.com/docs

> ⚠️ **Note**: First open Backend Api and then Frontend Api! (Services may take 30-60 seconds to wake up on first request (free tier cold start))

---

## ✨ Key Features

- **🧠 Multi-Provider LLM Support**: Choose from Mistral, OpenAI, Anthropic Claude, or Groq
- **💾 Flexible Storage**: Choose between local JSON files or MongoDB
- **🎯 Deterministic State Management**: LangGraph-inspired architecture eliminates LLM hallucination in context handling
- **💬 Natural Language Processing**: Understands queries like "What's the weather in Paris?"
- **📍 Smart Location Tracking**: State-based location persistence across conversation
- **🗺️ Comprehensive Travel Recommendations**: 
  - Tourist attractions (Overpass API + LLM suggestions)
  - Top restaurants and cafes
  - Recommended hotels and accommodations
- **☁️ Real-time Weather Data**: Current conditions with 7-day forecasts
- **⚡ Smart Caching**: 1-hour cache for weather and places data
- **🎨 Interactive UI**: Streamlit-based chat interface with debug mode
- **🐳 Docker Ready**: Full containerization with Docker Compose

---

## 🚀 Quick Start with Docker

### Prerequisites
- Docker and Docker Compose installed (for MongoDB setup)
- LLM API key (Mistral, OpenAI, Anthropic, or Groq)

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd Inkle-Assignment_AI-Intern
```

2. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env and configure:
# - Storage mode (local or mongodb)
# - LLM provider and API key
```

Example `.env` configuration:

**Option A: Local Storage (Simplest - No MongoDB needed)**
```bash
STORAGE_MODE=local
LLM_PROVIDER=mistral
MISTRAL_API_KEY=your_key_here
LOGGER=20
```

**Option B: MongoDB Storage (Persistent across restarts)**
```bash
STORAGE_MODE=mongodb
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=travel_agent_db
LLM_PROVIDER=mistral
MISTRAL_API_KEY=your_key_here
LOGGER=20
```

3. **Start the application**

**With Local Storage (No Database):**
```bash
# Start backend
cd backend
uvicorn app.main:app --reload

# Start frontend (in new terminal)
cd frontend
streamlit run app.py
```

**With MongoDB:**
```bash
# Start MongoDB + Backend + Frontend
docker-compose up -d
```

4. **Access the application**
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- API Health: http://localhost:8000/health

### Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Rebuild after code changes
docker-compose up -d --build

# Stop and remove everything including volumes
docker-compose down -v
```

## 🛠️ Local Development (without Docker)

### Storage Options

The app supports two storage modes:

1. **Local Storage** (Default)
   - Saves data to JSON files in `backend/data/` directory
   - No database setup required
   - Perfect for development and demos
   - ⚠️ Data stored locally (lost if folder deleted)

2. **MongoDB Storage**
   - Persistent database storage
   - Survives application restarts
   - Recommended for production
   - Requires MongoDB installation

Switch between modes by setting `STORAGE_MODE` in `.env`:
```bash
STORAGE_MODE=local      # Use JSON files (no MongoDB needed)
STORAGE_MODE=mongodb    # Use MongoDB (requires MONGO_URI)
```

### Backend Setup

1. **Create virtual environment**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r backend_requirements.txt
```

3. **Configure environment**
```bash
# Create .env file in project root with:
STORAGE_MODE=local                        # Use local JSON storage
LLM_PROVIDER=mistral                      # or openai, anthropic, groq
MISTRAL_API_KEY=your_api_key_here
LOGGER=20

# Optional - Only if using STORAGE_MODE=mongodb:
# MONGO_URI=mongodb://localhost:27017
# MONGO_DB_NAME=travel_agent_db
```

4. **Start MongoDB** (only if using STORAGE_MODE=mongodb)
```bash
mongod --dbpath /path/to/data
# Or use Docker:
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

5. **Run backend**
```bash
uvicorn app.main:app --reload
```

### Frontend Setup

1. **Create virtual environment**
```bash
cd frontend
python -m venv venv
source venv/bin/activate
```

2. **Install dependencies**
```bash
pip install -r frontend_requirements.txt
```

3. **Run frontend**
```bash
streamlit run app.py
```

## 🏗️ Architecture

### Multi-Provider LLM Support

The system supports multiple LLM providers through a unified interface:

**Supported Providers:**
- 🟣 **Mistral AI** - Cost-effective, fast (default)
- 🟢 **OpenAI** - GPT-3.5/GPT-4, highly reliable
- 🔵 **Anthropic** - Claude 3, excellent for long context
- ⚡ **Groq** - Ultra-fast inference with open models

**Configuration:**
```bash
# In .env file:
LLM_PROVIDER=mistral  # Choose: mistral, openai, anthropic, groq
MISTRAL_API_KEY=your_key_here
```

### State Management (LangGraph-Inspired)

This project uses a **deterministic state management** approach inspired by LangGraph to eliminate LLM hallucination in context handling.

**Key Concept:**
- **State = Single Source of Truth** stored per session
- **Updater Logic**: When user mentions "Paris", state updates `current_location = "Paris"`
- **Reader Logic**: When user says "weather there?", reads `current_location` from state (not from LLM context)
- **Result**: No hallucination, deterministic behavior
- **Storage**: Works with both local JSON files and MongoDB

📚 **Architecture & testing details**: [TESTING_GUIDE.md](./TESTING_GUIDE.md)

### Storage Architecture

**Local Storage Mode (`STORAGE_MODE=local`)**
```
backend/data/
├── chats/        # Chat history per session
├── state/        # Session state (location, shown places)
└── cache/        # Weather & places cache (1-hour expiry)
```

**MongoDB Mode (`STORAGE_MODE=mongodb`)**
- Collections: `chats`, `conversation_states`, `weather_cache`, `places_cache`
- Persistent across all restarts
- Suitable for production deployments

### Project Structure

```
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── core/        # Configuration, DB, LLM providers, State Management
│   │   │   ├── llm_connection.py      # Main LLM service
│   │   │   ├── llm_providers.py       # Provider implementations
│   │   │   └── config.py              # Multi-provider + storage settings
│   │   ├── models/      # Pydantic models
│   │   ├── repos/       # Database repositories
│   │   │   ├── base_repo.py          # MongoDB repository
│   │   │   └── local_repo.py         # Local JSON file repository
│   │   ├── routes/      # API routes
│   │   └── services/    # Business logic + State management
│   ├── data/           # Local storage (when STORAGE_MODE=local)
│   │   ├── chats/      # Chat history
│   │   ├── state/      # Session states
│   │   └── cache/      # Weather & places cache
│   ├── Dockerfile
│   └── backend_requirements.txt
│
├── frontend/            # Streamlit frontend
│   ├── app.py
│   ├── Dockerfile
│   └── frontend_requirements.txt
│
├── docker-compose.yml   # Docker orchestration
├── .env                 # Environment variables
├── LOCAL_STORAGE_GUIDE.md  # Local vs MongoDB storage guide
├── LLM_PROVIDERS.md     # Multi-provider configuration guide
├── LLM_QUICK_REFERENCE.md  # Quick LLM setup reference
├── TESTING_GUIDE.md     # Comprehensive testing + architecture guide
└── RUN.md               # Detailed run instructions
```

## 🔧 Technology Stack

- **Backend**: FastAPI, Uvicorn
- **Storage**: Local JSON files or MongoDB (async with Motor)
- **State Management**: LangGraph-inspired (langgraph, langchain-core)
- **Frontend**: Streamlit
- **LLM Providers**: Mistral AI, OpenAI, Anthropic Claude, Groq
- **APIs**: 
  - Open-Meteo (weather data)
  - Overpass API (tourist attractions)
  - Nominatim (geocoding)
  - LLM (restaurants & hotels suggestions)
- **Containerization**: Docker, Docker Compose

## 💡 How It Works

### Query Examples

**Weather Queries:**
```
"What's the weather in Tokyo?"
"Show me weather in Paris"
"Is it raining in Mumbai?"
```

**Places Queries:**
```
"Places to visit in London"
"Show me attractions in Dubai"
"I'm going to Bangkok, what can I visit?"
```

**Combined Queries:**
```
"Plan my trip to Singapore"
"I'm traveling to Rome, give me weather and places"
```

### Response Format

When you ask about places, you'll get three separate sections:

1. **🗺️ Places to Visit** - Tourist attractions, landmarks, museums (up to 8)
2. **🍽️ Top Restaurants** - Recommended restaurants and cafes (5)
3. **🏨 Recommended Hotels** - Top hotels and accommodations (5)

### Smart Features

- **Context Awareness**: Say "show me places there" after mentioning a city
- **No Repeats**: Ask "more places" to see additional suggestions without duplicates
- **Natural Language**: Talk naturally - "I'm going to Paris" works just like "Places in Paris"
- **Conversation Memory**: Maintains context throughout your session

## 📚 Documentation
storage comparison and deployment guide
- **[RUN.md](RUN.md)** - How to run the application (Docker, Python scripts, manual)
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Comprehensive testing scenarios

