#!/bin/bash

DJANGO_PORT=8080
DAPHNE_PORT=8082

# Function to kill process on a given port
kill_process_on_port() {
    local port=$1
    local pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        echo "Killing process on port $port (PID: $pid)"
        kill -9 $pid
        sleep 1  # Give it a moment to free up the port
    fi
}

# Kill processes on desired ports
kill_process_on_port $DJANGO_PORT
kill_process_on_port $DAPHNE_PORT

echo "Starting Django server on port $DJANGO_PORT"
echo "Starting Daphne server on port $DAPHNE_PORT"

# Run Django development server in the background
python3 manage.py runserver 0.0.0.0:$DJANGO_PORT --noreload &
DJANGO_PID=$!

# Run Daphne WebSocket server
daphne -p $DAPHNE_PORT -b 0.0.0.0 core.asgi:application

# When Daphne is stopped, also stop the Django server
kill $DJANGO_PID 2>/dev/null

echo "Servers stopped."
