# Use a Debian-based Python image
FROM python:3.11-slim-bullseye

# Install Redis and build tools
RUN apt-get update && apt-get install -y \
    redis-server \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && apt-get clean

# Set the working directory to /app
WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the ports for the application
EXPOSE 8000

# Start Redis and run Daphne
CMD redis-server --daemonize yes && \
    daphne -b 0.0.0.0 -p 8000 core.asgi:application
