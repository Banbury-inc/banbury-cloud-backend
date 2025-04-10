# Use a Debian-based Python image
FROM python:3.11-slim-bullseye

# Install Redis, Nginx, and build tools
RUN apt-get update && apt-get install -y \
    redis-server \
    nginx \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory to /app
WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Copy application code
COPY . .

# Copy nginx configuration
COPY nginx.conf /etc/nginx/sites-enabled/default

# Create health check script
RUN echo '#!/bin/bash\n\
curl -f http://localhost:8080/health/ || exit 1' > /app/healthcheck.sh
RUN chmod +x /app/healthcheck.sh

# Create startup script
RUN echo '#!/bin/bash\n\
redis-server --daemonize yes\n\
daphne -b 0.0.0.0 -p 8080 core.asgi:application &\n\
sleep 2\n\
exec nginx -g "daemon off;"' > /app/startup.sh
RUN chmod +x /app/startup.sh

# Expose the port Nginx listens on
EXPOSE 8080

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD /app/healthcheck.sh

# Start services using the startup script
CMD ["bash", "/app/startup.sh"]
