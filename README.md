# Inkle-Assignment_AI-Intern
Building a multi-agent tourism system with LangGraph-inspired state management

## ✨ Key Features

- **🧠 Multi-Provider LLM Support**: Choose from Mistral, OpenAI, Anthropic Claude, or Groq
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
- Docker and Docker Compose installed
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
# Edit .env and configure your LLM provider:
# - Set LLM_PROVIDER (mistral, openai, anthropic, or groq)
# - Add your API key for the chosen provider
```

Example `.env` configuration:
```bash
# Choose provider: mistral, openai, anthropic, or groq
LLM_PROVIDER=mistral
MISTRAL_API_KEY=your_key_here

# Or use OpenAI:
# LLM_PROVIDER=openai
# OPENAI_API_KEY=your_key_here
```

3. **Start all services**
```bash
docker-compose up -d
```

This will start:
- MongoDB on port 27017
- Backend API on port 8000
- Frontend UI on port 8501

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
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=travel_agent_db
LLM_PROVIDER=mistral  # or openai, anthropic, groq
MISTRAL_API_KEY=your_api_key_here
LOGGER=20
```

4. **Start MongoDB** (if not using Docker)
```bash
mongod --dbpath /path/to/data
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
- **State = Single Source of Truth** stored in MongoDB per session
- **Updater Logic**: When user mentions "Paris", state updates `current_location = "Paris"`
- **Reader Logic**: When user says "weather there?", reads `current_location` from state (not from LLM context)
- **Result**: No hallucination, deterministic behavior

📚 **Architecture & testing details**: [TESTING_GUIDE.md](./TESTING_GUIDE.md)

### Project Structure

```
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── core/        # Configuration, DB, LLM providers, State Management
│   │   │   ├── llm_connection.py      # Main LLM service
│   │   │   ├── llm_providers.py       # Provider implementations
│   │   │   └── config.py              # Multi-provider settings
│   │   ├── models/      # Pydantic models
│   │   ├── repos/       # Database repositories
│   │   ├── routes/      # API routes
│   │   └── services/    # Business logic + State management
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
├── LLM_PROVIDERS.md     # Multi-provider configuration guide
├── LLM_QUICK_REFERENCE.md  # Quick LLM setup reference
├── TESTING_GUIDE.md     # Comprehensive testing + architecture guide
└── RUN.md               # Detailed run instructions
```

## 🔧 Technology Stack

- **Backend**: FastAPI, Uvicorn, Motor (async MongoDB)
- **State Management**: LangGraph-inspired (langgraph, langchain-core)
- **Frontend**: Streamlit
- **Database**: MongoDB
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

- **[RUN.md](RUN.md)** - How to run the application (Docker, Python scripts, manual)
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Comprehensive testing scenarios
- **[LANGGRAPH_ARCHITECTURE.md](LANGGRAPH_ARCHITECTURE.md)** - State management deep dive
