# Use lightweight Python 3.11 image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py
ENV FLASK_ENV=production

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmariadb-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Remove PyQt5 since it is a GUI library not needed in server/docker
RUN grep -v "PyQt5" requirements.txt > requirements-prod.txt && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-prod.txt

# Copy the rest of the application
COPY . .

# Expose the port Flask runs on
EXPOSE 5001

# Command to run the application using Gunicorn or flask run
CMD ["python", "run.py"]
