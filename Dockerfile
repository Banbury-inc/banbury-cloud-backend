# Use a Debian-based Python image
FROM python:3.11-slim-bullseye

# Install Redis, build tools, and LibreOffice for PDF conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-server \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    curl \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
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

# Create health check script
RUN echo '#!/bin/bash\n\
curl -f http://localhost:8080/health/ || exit 1' > /app/healthcheck.sh
RUN chmod +x /app/healthcheck.sh

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
redis-server --daemonize yes\n\
# Optionally start schedulers inside the web container. Keep this disabled for ECS web services.\n\
if [ "${ENABLE_DAEMON:-false}" = "true" ]; then\n\
  echo "Starting TaskStudio daemon (adaptive, batch=${DAEMON_BATCH:-50})"\n\
  python manage.py process_taskstudio_daemon --adaptive --batch ${DAEMON_BATCH:-50} &\n\
  echo "Starting Flow Scheduler daemon (adaptive, batch=20)"\n\
  python manage.py process_flow_scheduler --adaptive --batch 20 &\n\
fi\n\
exec daphne -b 0.0.0.0 -p 8080 core.asgi:application' > /app/startup.sh
RUN chmod +x /app/startup.sh

# Expose the port Daphne listens on
EXPOSE 8080

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD /app/healthcheck.sh

# Start services using the startup script
CMD ["bash", "/app/startup.sh"]
