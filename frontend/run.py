#!/usr/bin/env python3
"""
Travel Agent Frontend - Run Script
This script starts the Streamlit frontend
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

def check_http_endpoint(url):
    """Check if HTTP endpoint is accessible"""
    try:
        import urllib.request
        urllib.request.urlopen(url, timeout=2)
        return True
    except:
        return False

def main():
    print_colored("🚀 Starting Travel Agent Frontend...", "blue")
    
    # Check if we're in the frontend directory
    check_file_exists("app.py", "app.py not found. Please run this script from the frontend directory.")
    
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
        import streamlit
    except ImportError:
        print_colored("❌ Dependencies not installed.", "red")
        print("Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "frontend_requirements.txt"], check=True)
    
    # Check if backend is running
    print_colored("🔍 Checking backend connection...", "blue")
    backend_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
    if not check_http_endpoint(f"{backend_url}/health"):
        print_colored(f"⚠️  Warning: Backend doesn't appear to be running at {backend_url}", "yellow")
        print("Please start the backend first:")
        print("  cd backend && python run.py")
        print()
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            sys.exit(1)
    
    # Start the Streamlit app
    print_colored("✅ All checks passed!", "green")
    print_colored("🌐 Starting Streamlit server...", "blue")
    print("📍 Frontend will be available at: http://localhost:8501")
    print()
    print("Press Ctrl+C to stop the server")
    print()
    
    # Run streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit",
            "run", "app.py"
        ], check=True)
    except KeyboardInterrupt:
        print_colored("\n👋 Frontend server stopped.", "yellow")
    except subprocess.CalledProcessError as e:
        print_colored(f"\n❌ Error starting server: {e}", "red")
        sys.exit(1)

if __name__ == "__main__":
    main()
