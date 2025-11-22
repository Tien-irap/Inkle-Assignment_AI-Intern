# 🚀 How to Run - Travel Agent AI

This guide covers different methods to run the Travel Agent AI application.

---

## 📋 Prerequisites

- Python 3.13 or higher
- MongoDB (local or Docker)
- Mistral AI API key

---

## 🐳 Method 1: Docker (Recommended)

The easiest way to run the entire application with all dependencies.

### 1. Install Docker Desktop
Download and install from [docker.com](https://www.docker.com/products/docker-desktop)

### 2. Configure Environment
```bash
# Create .env file in project root
cp .env.example .env

# Edit .env and add your Mistral API key
nano .env
```

Your `.env` should contain:
```env
MISTRAL_API_KEY=your_actual_api_key_here
```

### 3. Start All Services
```bash
# From project root
docker-compose up -d
```

This will start:
- MongoDB on port 27017
- Backend API on port 8000
- Frontend UI on port 8501

### 4. Access the Application
- **Frontend UI**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 5. View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f mongodb
```

### 6. Stop Services
```bash
# Stop and remove containers
docker-compose down

# Stop and remove everything including volumes
docker-compose down -v
```

---

## 🐍 Method 2: Using Python Run Scripts (Local Development)

Automated Python scripts that check dependencies and start services.

### Prerequisites
- MongoDB running locally on port 27017
- Python virtual environment

### 1. Start MongoDB
```bash
# Option A: Using Docker
docker run -d -p 27017:27017 --name mongodb mongo:7.0

# Option B: Local MongoDB
mongod --dbpath /path/to/data
```

### 2. Configure Environment
```bash
# Create .env in project root
cat > .env << EOF
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=travel_agent_db
MISTRAL_API_KEY=your_api_key_here
LOGGER=20
EOF
```

### 3. Create and Activate Virtual Environment
```bash
# Create virtual environment (if not already created)
python -m venv myenv

# Activate it
source myenv/bin/activate  # On macOS/Linux
# OR
myenv\Scripts\activate     # On Windows
```

### 4. Run Backend
```bash
cd backend
python run.py
```

The script will:
- ✅ Check if MongoDB is running
- ✅ Verify virtual environment is activated
- ✅ Install dependencies if needed
- ✅ Start Uvicorn server with colored output

**Backend available at:** http://localhost:8000

### 5. Run Frontend (in new terminal)
```bash
# Activate virtual environment first
source myenv/bin/activate  # On macOS/Linux

cd frontend
python run.py
```

The script will:
- ✅ Check if backend is running
- ✅ Verify virtual environment is activated
- ✅ Install dependencies if needed
- ✅ Start Streamlit server

**Frontend available at:** http://localhost:8501

---

## 📝 Method 3: Manual Setup (Step by Step)

For complete control over the setup process.

### Backend Setup

#### 1. Navigate to Backend
```bash
cd backend
```

#### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies
```bash
pip install -r backend_requirements.txt
```

#### 4. Configure Environment
Create `.env` file in **project root** (not backend folder):
```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=travel_agent_db
MISTRAL_API_KEY=your_api_key_here
LOGGER=20
```

#### 5. Start MongoDB
```bash
# Using Docker
docker run -d -p 27017:27017 mongo:7.0

# OR using local MongoDB
mongod --dbpath /path/to/data
```

#### 6. Run Backend
```bash
# Using Python module
python -m uvicorn app.main:app --reload

# OR using uvicorn directly
uvicorn app.main:app --reload
```

Backend will be available at: http://localhost:8000

---

### Frontend Setup

#### 1. Navigate to Frontend (in new terminal)
```bash
cd frontend
```

#### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies
```bash
pip install -r frontend_requirements.txt
```

#### 4. Run Frontend
```bash
# Using Python module
python -m streamlit run app.py

# OR using streamlit directly
streamlit run app.py
```

Frontend will be available at: http://localhost:8501

---

## 🔍 Verification

### 1. Check Backend Health
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```

### 2. Check Frontend
Open browser to http://localhost:8501

You should see the Travel Assistant AI interface.

### 3. Check MongoDB
```bash
# Using Docker
docker exec -it mongodb mongosh

# Using local MongoDB
mongosh

# In MongoDB shell
show dbs
use travel_agent_db
show collections
```

---

## 🐛 Troubleshooting

### Backend Won't Start

**Problem:** `Cannot connect to MongoDB`
```bash
# Check if MongoDB is running
docker ps | grep mongo
# OR
ps aux | grep mongod

# Start MongoDB if not running
docker run -d -p 27017:27017 mongo:7.0
```

**Problem:** `Module not found` errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r backend_requirements.txt
```

**Problem:** `MISTRAL_API_KEY not found`
```bash
# Check .env file exists in project root
cat ../.env

# Ensure it contains:
MISTRAL_API_KEY=your_key_here
```

**Problem:** `Virtual environment not activated` (when using run.py)
```bash
# Activate your virtual environment first
source myenv/bin/activate  # or venv/bin/activate

# Then run the script
python run.py
```

---

### Frontend Won't Start

**Problem:** `Cannot connect to backend`
```bash
# Verify backend is running
curl http://localhost:8000/health

# If not, start backend first
cd backend && python run.py
```

**Problem:** `streamlit: command not found`
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r frontend_requirements.txt
```

**Problem:** `Virtual environment not activated` (when using run.py)
```bash
# Activate your virtual environment first
source myenv/bin/activate

# Then run the script
python run.py
```

---

### Docker Issues

**Problem:** `Cannot connect to Docker daemon`
```bash
# Start Docker Desktop
open -a Docker  # macOS
# On Windows/Linux, start Docker Desktop manually

# Wait for Docker to start (check the menu bar icon)
```

**Problem:** Port already in use
```bash
# Check what's using the port
lsof -i :8000  # Backend
lsof -i :8501  # Frontend
lsof -i :27017 # MongoDB

# Stop the process or change port in docker-compose.yml
```

**Problem:** Container keeps restarting
```bash
# Check container logs
docker-compose logs backend

# Common issue: MongoDB not ready yet
# The docker-compose.yml has health checks, wait a moment
```

---

## 🔄 Quick Commands Reference

### Docker
```bash
# Start everything
docker-compose up -d

# Stop everything
docker-compose down

# View logs
docker-compose logs -f

# Rebuild containers
docker-compose up -d --build

# Check status
docker-compose ps
```

### Python Run Scripts
```bash
# Backend (from backend directory)
cd backend
python run.py

# Frontend (from frontend directory)
cd frontend
python run.py

# Make sure virtual environment is activated first!
source myenv/bin/activate  # or venv/bin/activate
```

### Manual Commands
```bash
# Backend
cd backend
python -m uvicorn app.main:app --reload

# Frontend
cd frontend
python -m streamlit run app.py
```

### MongoDB
```bash
# Start MongoDB (Docker)
docker run -d -p 27017:27017 --name mongodb mongo:7.0

# Stop MongoDB
docker stop mongodb

# Remove MongoDB container
docker rm mongodb

# Connect to MongoDB shell
mongosh
```

---

## 📊 Performance Tips

### Development Mode
- Use `--reload` flag for auto-restart on code changes
- Keep backend logs visible for debugging
- Enable debug mode in frontend sidebar
- Use Python run scripts for automated checks

### Production Mode
- Remove `--reload` flag from uvicorn
- Set `LOGGER=30` in .env (WARNING level)
- Use gunicorn or multiple uvicorn workers
- Configure nginx reverse proxy
- Use managed MongoDB (Atlas, etc.)

---

## 🆘 Getting Help

If you encounter issues:

1. **Check logs**: 
   - Docker: `docker-compose logs -f`
   - Local: Check terminal output where backend/frontend is running
2. **Verify .env**: Ensure all required variables are set in project root
3. **Test APIs**: Use curl or browser to test http://localhost:8000/health
4. **Check ports**: Ensure 8000, 8501, 27017 are not in use
5. **Virtual environment**: Ensure it's activated before running Python scripts
6. **Review TESTING_GUIDE.md**: Contains detailed test scenarios

---

## 📝 Notes

- **Development**: Use Python run scripts (`run.py`) for automated setup and checks
- **Production**: Use Docker for consistent deployment across environments
- **MongoDB**: Docker MongoDB is ephemeral unless you configure volumes
- **API Keys**: Never commit .env files with real API keys to git
- **Ports**: You can change ports in docker-compose.yml if needed
- **Virtual Environment**: Both `venv` and `myenv` are gitignored, use either name
- **Python Scripts**: The `run.py` scripts have colored output and helpful error messages
