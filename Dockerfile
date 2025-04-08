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

# Create startup script
COPY . .
RUN echo '#!/bin/bash\n\
redis-server --daemonize yes\n\
python3 manage.py runserver 0.0.0.0:8080 --noreload &\n\
exec daphne -b 0.0.0.0 -p 8082 core.asgi:application' > /app/startup.sh
RUN chmod +x /app/startup.sh

# Expose the ports for the application
EXPOSE 8080 8082

# Start services using JSON array format
CMD ["bash", "/app/startup.sh"]
