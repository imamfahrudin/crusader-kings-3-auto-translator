FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY config.json .

# Create necessary directories
RUN mkdir -p input temp output

# Set environment variables
ENV TEMP_DIR=/app/temp

# Run the application
CMD ["python", "main.py"]