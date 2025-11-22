FROM python:3.13-slim

WORKDIR /app

# Copy requirements first for better caching
COPY frontend_requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r frontend_requirements.txt

# Copy application code
COPY . .

# Expose the port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
