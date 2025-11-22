FROM python:3.13-slim

WORKDIR /app

# Copy requirements first for better caching
COPY backend_requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r backend_requirements.txt

# Copy application code
COPY . .

# Expose the port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
