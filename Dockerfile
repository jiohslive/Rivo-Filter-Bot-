# ---- Dockerfile for VJ Filter Bot ----
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies for building tgcrypto
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libffi-dev \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# Expose port (optional, only if needed)
# EXPOSE 8080

# Run the bot
CMD ["python", "bot.py"]
