#!/usr/bin/env python3
"""
Travel Agent Backend - Run Script
This script starts the FastAPI backend server
"""

import os
import sys
import subprocess
import socket
from pathlib import Path

def print_colored(message, color="blue"):
    """Print colored output"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}{message}{colors['reset']}")

def check_file_exists(filepath, error_message):
    """Check if a file exists"""
    if not Path(filepath).exists():
        print_colored(f"❌ Error: {error_message}", "red")
        sys.exit(1)

def check_port_open(host, port):
    """Check if a port is open"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0

def main():
    print_colored("🚀 Starting Travel Agent Backend...", "blue")
    
    # Check if we're in the backend directory
    check_file_exists("app/main.py", "app/main.py not found. Please run this script from the backend directory.")
    
    # Check if .env exists in parent directory
    env_path = Path("../.env")
    if not env_path.exists():
        print_colored("⚠️  Warning: .env file not found in project root.", "yellow")
        print("Please create a .env file with the following variables:")
        print("  MONGO_URI=mongodb://localhost:27017")
        print("  MONGO_DB_NAME=travel_agent_db")
        print("  MISTRAL_API_KEY=your_api_key_here")
        print("  LOGGER=20")
        sys.exit(1)
    
    # Check if MongoDB is running
    print_colored("🔍 Checking MongoDB connection...", "blue")
    if not check_port_open("localhost", 27017):
        print_colored("⚠️  Warning: MongoDB doesn't appear to be running on localhost:27017", "yellow")
        print("Please start MongoDB first:")
        print("  - Using Docker: docker run -d -p 27017:27017 mongo:7.0")
        print("  - Using local installation: mongod --dbpath /path/to/data")
        print()
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            sys.exit(1)
    
    # Check if virtual environment is activated
    if not os.environ.get('VIRTUAL_ENV'):
        print_colored("⚠️  Virtual environment not activated.", "yellow")
        print("Please activate your virtual environment first:")
        print("  source venv/bin/activate  # On macOS/Linux")
        print("  venv\\Scripts\\activate     # On Windows")
        sys.exit(1)
    
    # Check if dependencies are installed
    print_colored("🔍 Checking dependencies...", "blue")
    try:
        import fastapi
        import uvicorn
    except ImportError:
        print_colored("❌ Dependencies not installed.", "red")
        print("Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "backend_requirements.txt"], check=True)
    
    # Start the server
    print_colored("✅ All checks passed!", "green")
    print_colored("🌐 Starting Uvicorn server...", "blue")
    print("📍 Backend will be available at: http://localhost:8000")
    print("📍 API Health check: http://localhost:8000/health")
    print("📍 API Documentation: http://localhost:8000/docs")
    print()
    print("Press Ctrl+C to stop the server")
    print()
    
    # Run uvicorn with auto-reload for development
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--reload",
            "--host", "0.0.0.0",
            "--port", "8000"
        ], check=True)
    except KeyboardInterrupt:
        print_colored("\n👋 Backend server stopped.", "yellow")
    except subprocess.CalledProcessError as e:
        print_colored(f"\n❌ Error starting server: {e}", "red")
        sys.exit(1)

if __name__ == "__main__":
    main()
