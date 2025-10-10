# Dockerfile for GENESIS AI Assistant (Middleware Brain)

# Use a recent stable Python runtime
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed by Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file
COPY requirements.txt ./

# Install core Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Download the spaCy model
RUN python -m spacy download en_core_web_sm

# Create the data directory and ensure permissions
RUN mkdir -p /app/data && chmod -R 777 /app/data

# Command to run the application 
ENTRYPOINT ["python", "main.py"]