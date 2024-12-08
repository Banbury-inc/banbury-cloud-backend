# Python image to use.
FROM python:3.11-alpine

# Install system dependencies for Redis and build tools
RUN apk add --no-cache \
    redis \
    build-base \
    gcc \
    musl-dev \
    libffi-dev \
    python3-dev \
    py3-pip \
    && pip install --upgrade pip

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file used for dependencies
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Copy the rest of the working directory contents into the container at /app
COPY . .

# Expose the port for the application
EXPOSE 8080

# Start Redis in the background and then start the Django app with Daphne
CMD redis-server --daemonize yes && daphne -b 0.0.0.0 -p 8080 helloproject.asgi:application

