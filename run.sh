#!/bin/bash

DJANGO_PORT=8080
DAPHNE_PORT=8082
CONTAINER_NAME="banbury-backend"
IMAGE_NAME="banbury-backend-image"

# Parse arguments
USE_DOCKER=false
ACTION="start"

# Process arguments
for arg in "$@"; do
    case $arg in
        --docker)
            USE_DOCKER=true
            ;;
        start|stop|restart|logs|stream-logs)
            ACTION=$arg
            ;;
    esac
done

# Function to check if a port is available
is_port_available() {
    local port=$1
    # Try with lsof first
    if command -v lsof &> /dev/null; then
        # lsof returns 0 when port is in use, 1 when it's not in use
        # We want to return 0 when port IS available (not in use)
        if lsof -i:"$port" &> /dev/null; then
            # Port is in use
            return 1
        else
            # Port is available
            return 0
        fi
    # Try with netstat as an alternative
    elif command -v netstat &> /dev/null; then
        if netstat -tuln | grep ":$port " &> /dev/null; then
            # Port is in use
            return 1
        else
            # Port is available
            return 0
        fi
    # Try with ss as another alternative
    elif command -v ss &> /dev/null; then
        if ss -tuln | grep ":$port " &> /dev/null; then
            # Port is in use
            return 1
        else
            # Port is available
            return 0
        fi
    # Try with nc as a last resort
    elif command -v nc &> /dev/null; then
        # Check if we can bind to the port
        # If successful, port is available
        if (nc -z localhost "$port") &> /dev/null; then
            return 1
        else
            return 0
        fi
    else
        # If all else fails, try a direct socket connection
        # This may not work on all systems
        if (echo > /dev/tcp/localhost/"$port") &> /dev/null; then
            # If we can connect, port is in use
            return 1
        else
            # Connection failed, port may be available
            return 0
        fi
    fi
}

# Function to kill process on a given port
kill_process_on_port() {
    local port=$1
    local pid=$(lsof -ti:$port)
    
    if [ -z "$pid" ]; then
        # Try with sudo to get all processes (including system ones)
        if command -v sudo &> /dev/null; then
            pid=$(sudo lsof -ti:$port)
        fi
        
        if [ -z "$pid" ]; then
            echo "No process found using port $port"
            return 1
        fi
    fi
    
    echo "Found process using port $port (PID: $pid)"
    
    # Try to kill normally first
    if kill -9 $pid 2>/dev/null; then
        echo "Successfully killed process on port $port"
        sleep 1  # Give it a moment to free up the port
        return 0
    fi
    
    # If normal kill fails, try with sudo
    if command -v sudo &> /dev/null; then
        echo "Normal kill failed. Attempting with sudo..."
        if sudo kill -9 $pid 2>/dev/null; then
            echo "Successfully killed process on port $port with sudo"
            sleep 1
            return 0
        fi
    fi
    
    echo "Failed to kill process on port $port. Process might require elevated privileges."
    return 1
}

# Docker-related functions
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "Docker is not installed. Please install Docker first."
        exit 1
    fi
}

# Check if container exists (running or stopped)
container_exists() {
    docker container ls -a --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "$CONTAINER_NAME"
    return $?
}

# Check if container is running
container_running() {
    docker container ls --filter "name=$CONTAINER_NAME" --filter "status=running" --format "{{.Names}}" | grep -q "$CONTAINER_NAME"
    return $?
}

# Stop and remove container if it exists
stop_container() {
    if container_exists; then
        echo "Removing existing container $CONTAINER_NAME..."
        docker rm -f $CONTAINER_NAME > /dev/null 2>&1
        return $?
    fi
    return 0
}

# Verify if a port is actually in use
verify_port_in_use() {
    local port=$1
    local processes=$(lsof -i:"$port" 2>/dev/null)
    
    if [ -z "$processes" ] && command -v sudo &> /dev/null; then
        processes=$(sudo lsof -i:"$port" 2>/dev/null)
    fi
    
    if [ -z "$processes" ]; then
        # Double check with other tools
        if command -v netstat &> /dev/null && ! netstat -tuln | grep ":$port " &> /dev/null; then
            return 1  # Port not actually in use
        elif command -v ss &> /dev/null && ! ss -tuln | grep ":$port " &> /dev/null; then
            return 1  # Port not actually in use
        fi
    fi
    
    return 0  # Port is in use or we can't verify it's not
}

# Check host ports before starting container
check_host_ports() {
    local has_conflicts=false
    local conflict_ports=""
    local conflict_ports_array=()

    # Check Django port
    if ! is_port_available $DJANGO_PORT; then
        # Verify port is actually in use before reporting a conflict
        if verify_port_in_use $DJANGO_PORT; then
            has_conflicts=true
            conflict_ports="$DJANGO_PORT"
            conflict_ports_array+=($DJANGO_PORT)
        fi
    fi

    # Check Daphne port
    if ! is_port_available $DAPHNE_PORT; then
        # Verify port is actually in use before reporting a conflict
        if verify_port_in_use $DAPHNE_PORT; then
            has_conflicts=true
            if [ -z "$conflict_ports" ]; then
                conflict_ports="$DAPHNE_PORT"
            else
                conflict_ports="$conflict_ports, $DAPHNE_PORT"
            fi
            conflict_ports_array+=($DAPHNE_PORT)
        fi
    fi

    if $has_conflicts; then
        echo "Error: Port(s) $conflict_ports already in use on the host system."
        echo "Options:"
        echo "  1. Stop the processes using these ports"
        echo "  2. Edit run.sh to use different ports"
        echo "  3. Run 'lsof -i:$DJANGO_PORT' and 'lsof -i:$DAPHNE_PORT' to identify processes"
        echo "  4. Quit"
        
        # Interactive prompt
        read -p "Choose an option (1-4): " option
        
        case $option in
            1)
                echo "Attempting to stop processes using the conflicting ports..."
                
                # Try to kill processes on each conflicting port
                local all_killed=true
                for port in "${conflict_ports_array[@]}"; do
                    if ! kill_process_on_port $port; then
                        echo "Failed to kill process on port $port"
                        all_killed=false
                    fi
                done
                
                # Verify ports are now available
                if $all_killed; then
                    for port in "${conflict_ports_array[@]}"; do
                        if ! is_port_available $port; then
                            echo "Port $port is still in use. Failed to free up the port."
                            echo "Try manually: sudo lsof -i:$port (to see process)"
                            echo "Then: sudo kill -9 <PID> (to kill it)"
                            return 1
                        fi
                    done
                    echo "Successfully freed all required ports."
                    return 0
                else
                    echo "Failed to free up all ports."
                    echo "You may need to run this script with sudo for privileged ports."
                    return 1
                fi
                ;;
            2)
                echo "Please edit the run.sh script to change the port values."
                return 1
                ;;
            3)
                for port in "${conflict_ports_array[@]}"; do
                    echo "Processes using port $port:"
                    if command -v sudo &> /dev/null; then
                        sudo lsof -i:$port || echo "No process found using port $port"
                    else
                        lsof -i:$port || echo "No process found using port $port"
                    fi
                done
                return 1
                ;;
            4|*)
                echo "Operation cancelled."
                return 1
                ;;
        esac
    fi

    return 0
}

# Start Docker container
start_container() {
    if ! stop_container; then
        echo "Failed to remove existing container. Please check Docker status."
        return 1
    fi
    
    # Check if ports are available on host before starting
    if ! check_host_ports; then
        return 1
    fi
    
    echo "Building Docker image..."
    if ! docker build -t $IMAGE_NAME .; then
        echo "Docker build failed."
        return 1
    fi
    
    echo "Starting container $CONTAINER_NAME..."
    if ! docker run --name $CONTAINER_NAME -p $DJANGO_PORT:8080 -p $DAPHNE_PORT:8082 -d $IMAGE_NAME; then
        echo "Failed to start Docker container."
        return 1
    fi
    
    echo "Container started successfully."
    echo "Django available at http://localhost:$DJANGO_PORT"
    echo "Daphne available at ws://localhost:$DAPHNE_PORT"
    return 0
}

# Stream container logs with continuous following
stream_container_logs() {
    if ! container_exists; then
        echo "Container not found. Start it first with: $0 --docker start"
        return 1
    fi

    if ! container_running; then
        echo "Container exists but is not running. Start it with: $0 --docker start"
        return 1
    fi

    echo "Starting continuous log streaming. Press Ctrl+C to exit..."
    echo "---------------------------------------------------------------"
    
    # Don't use exec - it's causing issues in some shells
    # Instead, run directly and use a trap to handle the Ctrl+C gracefully
    trap 'echo -e "\nLog streaming ended."; exit 0' INT
    
    # Use the --follow flag to keep streaming logs
    # Set --tail to show recent logs first, then continue streaming
    docker logs --follow --tail=100 $CONTAINER_NAME
    
    # This line will only be reached if docker logs exits unexpectedly
    echo "Log streaming ended."
}

# Main execution logic
if [ "$USE_DOCKER" = true ]; then
    # Docker execution path
    check_docker
    
    case "$ACTION" in
        "start")
            start_container
            ;;
        "stop")
            if container_exists; then
                stop_container
                echo "Container stopped and removed."
            else
                echo "No container found to stop."
            fi
            ;;
        "restart")
            start_container
            ;;
        "logs")
            if container_exists; then
                # Show logs without following
                docker logs $CONTAINER_NAME
            else
                echo "Container not found. Start it first with: $0 --docker start"
            fi
            ;;
        "stream-logs")
            stream_container_logs
            ;;
        *)
            echo "Usage: $0 [--docker] [start|stop|restart|logs|stream-logs]"
            echo "  start       - Start services"
            echo "  stop        - Stop services"
            echo "  restart     - Restart services"
            echo "  logs        - View container logs (past logs only)"
            echo "  stream-logs - Stream container logs in real-time"
            ;;
    esac
else
    # Direct execution path
    case "$ACTION" in
        "start"|"restart")
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
            ;;
        "stop")
            kill_process_on_port $DJANGO_PORT
            kill_process_on_port $DAPHNE_PORT
            echo "Servers stopped."
            ;;
        "logs"|"stream-logs")
            echo "Logs are not available when running directly."
            echo "Use --docker to run in Docker if you need to view logs."
            ;;
        *)
            echo "Usage: $0 [--docker] [start|stop|restart|logs|stream-logs]"
            echo "  start       - Start services"
            echo "  stop        - Stop services"
            echo "  restart     - Restart services"
            echo "  logs        - View container logs (past logs only)"
            echo "  stream-logs - Stream container logs in real-time"
            ;;
    esac
fi
