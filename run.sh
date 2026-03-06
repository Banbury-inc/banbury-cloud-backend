#!/bin/bash

HTTP_PORT=8080
CONTAINER_NAME="banbury-backend"
IMAGE_NAME="banbury-backend-image"
DAEMON_CONTAINER_NAME="banbury-backend-daemon"
DAEMON_INTERVAL=${DAEMON_INTERVAL:-30}
DAEMON_BATCH=${DAEMON_BATCH:-50}
DAEMON_MODE=${DAEMON_MODE:-"adaptive"}  # "adaptive", "realtime", or "fixed"
DAEMON_PID_FILE="taskstudio_daemon.pid"
DAEMON_LOG_FILE="taskstudio_daemon.log"
FLOW_DAEMON_PID_FILE="flow_scheduler_daemon.pid"
FLOW_DAEMON_LOG_FILE="flow_scheduler_daemon.log"

# Parse arguments
USE_DOCKER=false
ACTION="start"

# Process arguments
for arg in "$@"; do
    case $arg in
        --docker)
            USE_DOCKER=true
            ;;
        start|stop|restart|logs|stream-logs|start-daemon|stop-daemon|restart-daemon|logs-daemon|stream-logs-daemon|start-all|start-daemon-foreground)
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

# Function to kill all flow scheduler daemon processes
kill_all_flow_daemons() {
    echo "🔍 Checking for existing Flow Scheduler daemon processes..."
    local pids=()
    if command -v pgrep &> /dev/null; then
        local pgrep_pids=$(pgrep -f "process_flow_scheduler" 2>/dev/null | tr '\n' ' ')
        if [ -n "$pgrep_pids" ]; then
            pids+=($pgrep_pids)
        fi
    fi
    local ps_pids=$(ps aux | grep -E "process_flow_scheduler" | grep -v grep | awk '{print $2}' | tr '\n' ' ')
    if [ -n "$ps_pids" ]; then
        pids+=($ps_pids)
    fi
    if [ -f "$FLOW_DAEMON_PID_FILE" ]; then
        local file_pid=$(cat "$FLOW_DAEMON_PID_FILE" 2>/dev/null)
        if [ -n "$file_pid" ] && kill -0 "$file_pid" 2>/dev/null; then
            pids+=($file_pid)
        fi
    fi
    local unique_pids=($(printf "%s\n" "${pids[@]}" | sort -u | grep -v '^$'))
    if [ ${#unique_pids[@]} -eq 0 ]; then
        echo "✅ No existing Flow Scheduler daemon processes found"
        return 0
    fi
    echo "🛑 Found ${#unique_pids[@]} Flow Scheduler daemon process(es): ${unique_pids[*]}"
    local killed_count=0
    for pid in "${unique_pids[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "   Killing daemon PID $pid..."
            if kill -TERM "$pid" 2>/dev/null; then
                sleep 2
                if kill -0 "$pid" 2>/dev/null; then
                    kill -KILL "$pid" 2>/dev/null || true
                fi
                killed_count=$((killed_count + 1))
                echo "   ✓ Daemon PID $pid stopped"
            else
                echo "   ⚠️  Failed to kill daemon PID $pid"
            fi
        fi
    done
    rm -f "$FLOW_DAEMON_PID_FILE" 2>/dev/null || true
    echo "✅ Killed $killed_count Flow Scheduler daemon process(es)"
    return 0
}

# Function to kill all TaskStudio daemon processes
kill_all_taskstudio_daemons() {
    echo "🔍 Checking for existing TaskStudio daemon processes..."
    
    # Find all TaskStudio daemon processes using different methods
    local pids=()
    
    # Method 1: Using pgrep
    if command -v pgrep &> /dev/null; then
        local pgrep_pids=$(pgrep -f "process_taskstudio_daemon\|process_taskstudio_realtime" 2>/dev/null | tr '\n' ' ')
        if [ -n "$pgrep_pids" ]; then
            pids+=($pgrep_pids)
        fi
    fi
    
    # Method 2: Using ps and grep
    local ps_pids=$(ps aux | grep -E "(process_taskstudio_daemon|process_taskstudio_realtime)" | grep -v grep | awk '{print $2}' | tr '\n' ' ')
    if [ -n "$ps_pids" ]; then
        pids+=($ps_pids)
    fi
    
    # Method 3: Check PID file
    if [ -f "$DAEMON_PID_FILE" ]; then
        local file_pid=$(cat "$DAEMON_PID_FILE" 2>/dev/null)
        if [ -n "$file_pid" ] && kill -0 "$file_pid" 2>/dev/null; then
            pids+=($file_pid)
        fi
    fi
    
    # Remove duplicates and empty values
    local unique_pids=($(printf "%s\n" "${pids[@]}" | sort -u | grep -v '^$'))
    
    if [ ${#unique_pids[@]} -eq 0 ]; then
        echo "✅ No existing TaskStudio daemon processes found"
        return 0
    fi
    
    echo "🛑 Found ${#unique_pids[@]} TaskStudio daemon process(es): ${unique_pids[*]}"
    
    # Kill each process
    local killed_count=0
    for pid in "${unique_pids[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "   Killing daemon PID $pid..."
            if kill -TERM "$pid" 2>/dev/null; then
                # Give it a moment to terminate gracefully
                sleep 2
                if kill -0 "$pid" 2>/dev/null; then
                    # Force kill if still running
                    kill -KILL "$pid" 2>/dev/null || true
                fi
                killed_count=$((killed_count + 1))
                echo "   ✓ Daemon PID $pid stopped"
            else
                echo "   ⚠️  Failed to kill daemon PID $pid"
            fi
        fi
    done
    
    # Clean up PID file
    rm -f "$DAEMON_PID_FILE" 2>/dev/null || true
    
    echo "✅ Killed $killed_count TaskStudio daemon process(es)"
    return 0
}

# Function to get the appropriate daemon command based on DAEMON_MODE
get_daemon_command() {
    local python_bin="$1"
    case "$DAEMON_MODE" in
        "realtime")
            echo "$python_bin manage.py process_taskstudio_realtime --initial-scan --batch $DAEMON_BATCH"
            ;;
        "fixed")
            echo "$python_bin manage.py process_taskstudio_daemon --interval $DAEMON_INTERVAL --batch $DAEMON_BATCH"
            ;;
        "adaptive"|*)
            echo "$python_bin manage.py process_taskstudio_daemon --adaptive --batch $DAEMON_BATCH"
            ;;
    esac
}

# Function to get daemon mode description
get_daemon_description() {
    case "$DAEMON_MODE" in
        "realtime")
            echo "real-time event-driven processing"
            ;;
        "fixed")
            echo "fixed ${DAEMON_INTERVAL}s polling"
            ;;
        "adaptive"|*)
            echo "adaptive polling"
            ;;
    esac
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

# Start daemon container
start_daemon_container() {
    echo "Starting daemon container $DAEMON_CONTAINER_NAME..."
    # Remove any existing daemon container
    docker rm -f $DAEMON_CONTAINER_NAME > /dev/null 2>&1 || true
    
    # Determine daemon command based on mode preference
    local daemon_cmd=$(get_daemon_command "python")
    local daemon_desc=$(get_daemon_description)
    
    # Pass through environment needed by the daemon
    docker run --name $DAEMON_CONTAINER_NAME -d \
        -e BANBURY_WEBSITE_ORIGIN=${BANBURY_WEBSITE_ORIGIN:-http://localhost:3000} \
        -e BANBURY_API_BASE=${BANBURY_API_BASE:-http://localhost:8080} \
        -e DAEMON_BEARER=${DAEMON_BEARER:-} \
        -e MONGO_URI=${MONGO_URI:-} \
        $IMAGE_NAME \
        sh -c "$daemon_cmd"
    if [ $? -ne 0 ]; then
        echo "Failed to start daemon container."
        return 1
    fi
    echo "✅ Daemon container started successfully with $daemon_desc."
    return 0
}

# Stop daemon container
stop_daemon_container() {
    if docker container ls -a --filter "name=$DAEMON_CONTAINER_NAME" --format "{{.Names}}" | grep -q "$DAEMON_CONTAINER_NAME"; then
        echo "Stopping daemon container $DAEMON_CONTAINER_NAME..."
        docker rm -f $DAEMON_CONTAINER_NAME > /dev/null 2>&1
        echo "Daemon container stopped."
    else
        echo "No daemon container found to stop."
    fi
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

    # Check HTTP port
    if ! is_port_available $HTTP_PORT; then
        # Verify port is actually in use before reporting a conflict
        if verify_port_in_use $HTTP_PORT; then
            has_conflicts=true
            conflict_ports="$HTTP_PORT"
            conflict_ports_array+=($HTTP_PORT)
        fi
    fi

    if $has_conflicts; then
        echo "Error: Port(s) $conflict_ports already in use on the host system."
        echo "Options:"
        echo "  1. Stop the processes using these ports"
        echo "  2. Edit run.sh to use different ports (HTTP_PORT=$HTTP_PORT)"
        echo "  3. Run 'lsof -i:$HTTP_PORT' to identify processes"
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
                        sudo lsof -i:$port || echo "No process found using port $port (maybe free or needs sudo)"
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
    if ! docker run --name $CONTAINER_NAME -p $HTTP_PORT:8080 -d $IMAGE_NAME; then
        echo "Failed to start Docker container."
        return 1
    fi
    
    echo "Container started successfully."
    echo "Application available at http://localhost:$HTTP_PORT"
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
            echo ""
            echo "Actions:"
            echo "  start       - Start services"
            echo "  stop        - Stop services"
            echo "  restart     - Restart services"
            echo "  logs        - View container logs (past logs only)"
            echo "  stream-logs - Stream container logs in real-time"
            echo ""
            echo "Environment Variables:"
            echo "  DAEMON_MODE     - Daemon mode: 'adaptive' (default), 'realtime', or 'fixed'"
            echo "  DAEMON_BATCH    - Max tasks per batch (default: 50)"
            echo "  DAEMON_INTERVAL - Polling interval for fixed mode (default: 30s)"
            echo "  HTTP_PORT       - Server port (default: 8080)"
            ;;
    esac
else
    # Direct execution path (Simplified - only uses Daphne)
    case "$ACTION" in
        "start"|"restart")
            # Kill process on the app port
            kill_process_on_port $HTTP_PORT
            
            # Kill all existing daemons
            kill_all_taskstudio_daemons
            kill_all_flow_daemons

            echo "Starting Daphne server on port $HTTP_PORT"
            PYTHON_BIN=${PYTHON_BIN:-venv/bin/python}
            if [ ! -x "$PYTHON_BIN" ]; then
                PYTHON_BIN=$(command -v python3 || command -v python)
            fi
            if [ -z "$PYTHON_BIN" ]; then
                echo "No python interpreter found (venv/bin/python, python3, or python). Cannot start daemons."
            else
                local daemon_cmd=$(get_daemon_command "$PYTHON_BIN")
                local daemon_desc=$(get_daemon_description)
                echo "🚀 Starting TaskStudio daemon with $daemon_desc (batch=$DAEMON_BATCH)"
                nohup $daemon_cmd > "$DAEMON_LOG_FILE" 2>&1 &
                echo $! > "$DAEMON_PID_FILE"
                echo "✅ TaskStudio daemon PID $(cat "$DAEMON_PID_FILE") logging to $DAEMON_LOG_FILE"

                echo "🚀 Starting Flow Scheduler daemon with adaptive polling"
                nohup $PYTHON_BIN manage.py process_flow_scheduler --adaptive --batch 20 > "$FLOW_DAEMON_LOG_FILE" 2>&1 &
                echo $! > "$FLOW_DAEMON_PID_FILE"
                echo "✅ Flow Scheduler daemon PID $(cat "$FLOW_DAEMON_PID_FILE") logging to $FLOW_DAEMON_LOG_FILE"
            fi

            daphne -p $HTTP_PORT -b 0.0.0.0 core.asgi:application

            echo "Server stopped."
            ;;
        "stop")
            kill_process_on_port $HTTP_PORT
            kill_all_taskstudio_daemons
            kill_all_flow_daemons
            echo "Server stopped."
            ;;
        "start-daemon")
            # Kill all existing TaskStudio daemons first
            kill_all_taskstudio_daemons
            
            PYTHON_BIN=${PYTHON_BIN:-venv/bin/python}
            if [ ! -x "$PYTHON_BIN" ]; then
                PYTHON_BIN=$(command -v python3 || command -v python)
            fi
            if [ -z "$PYTHON_BIN" ]; then
                echo "No python interpreter found (venv/bin/python, python3, or python)."
                exit 1
            fi
            local daemon_cmd=$(get_daemon_command "$PYTHON_BIN")
            local daemon_desc=$(get_daemon_description)
            echo "🚀 Starting TaskStudio daemon with $daemon_desc (batch=$DAEMON_BATCH)"
            nohup $daemon_cmd > "$DAEMON_LOG_FILE" 2>&1 &
            echo $! > "$DAEMON_PID_FILE"
            echo "✅ Daemon PID $(cat "$DAEMON_PID_FILE") logging to $DAEMON_LOG_FILE"
            ;;
        "stop-daemon")
            kill_all_taskstudio_daemons
            ;;
        "logs-daemon")
            if [ -f "$DAEMON_LOG_FILE" ]; then
                echo "Tailing daemon log ($DAEMON_LOG_FILE). Press Ctrl+C to exit."
                tail -f "$DAEMON_LOG_FILE"
            else
                echo "Daemon log not found ($DAEMON_LOG_FILE)."
            fi
            ;;
        "start-daemon-foreground")
            PYTHON_BIN=${PYTHON_BIN:-venv/bin/python}
            if [ ! -x "$PYTHON_BIN" ]; then
                PYTHON_BIN=$(command -v python3 || command -v python)
            fi
            if [ -z "$PYTHON_BIN" ]; then
                echo "No python interpreter found (venv/bin/python, python3, or python)."
                exit 1
            fi
            
            # Kill any existing processes on the ports
            kill_process_on_port $HTTP_PORT
            kill_all_taskstudio_daemons
            kill_all_flow_daemons
            
            local daemon_desc=$(get_daemon_description)
            echo "Starting Daphne server, TaskStudio daemon, AND Flow Scheduler daemon in FOREGROUND"
            echo "Server on port $HTTP_PORT, TaskStudio ($daemon_desc, batch=$DAEMON_BATCH)"
            echo "Press Ctrl+C to stop all services"
            echo "=========================================="
            
            # Start task daemon in background
            local daemon_cmd=$(get_daemon_command "$PYTHON_BIN")
            echo "🔧 Starting TaskStudio daemon with $daemon_desc..."
            $daemon_cmd &
            DAEMON_PID=$!
            echo "✓ TaskStudio daemon started with PID $DAEMON_PID"

            # Start flow scheduler daemon in background
            echo "🔧 Starting Flow Scheduler daemon with adaptive polling..."
            $PYTHON_BIN manage.py process_flow_scheduler --adaptive --batch 20 &
            FLOW_DAEMON_PID=$!
            echo "✓ Flow Scheduler daemon started with PID $FLOW_DAEMON_PID"
            
            cleanup() {
                echo ""
                echo "🛑 Shutting down services..."
                if kill -0 $DAEMON_PID 2>/dev/null; then
                    echo "   Stopping TaskStudio daemon (PID $DAEMON_PID)..."
                    kill -TERM $DAEMON_PID 2>/dev/null || true
                fi
                if kill -0 $FLOW_DAEMON_PID 2>/dev/null; then
                    echo "   Stopping Flow Scheduler daemon (PID $FLOW_DAEMON_PID)..."
                    kill -TERM $FLOW_DAEMON_PID 2>/dev/null || true
                fi
                sleep 2
                kill -KILL $DAEMON_PID 2>/dev/null || true
                kill -KILL $FLOW_DAEMON_PID 2>/dev/null || true
                kill_process_on_port $HTTP_PORT
                echo "✓ All services stopped"
                exit 0
            }
            
            trap cleanup INT TERM
            sleep 2
            
            echo "🌐 Starting Daphne server on port $HTTP_PORT..."
            echo "----------------------------------------"
            
            daphne -p $HTTP_PORT -b 0.0.0.0 core.asgi:application
            cleanup
            ;;
        "logs"|"stream-logs")
            echo "Logs are not available when running directly."
            echo "Use --docker to run in Docker if you need to view logs."
            ;;
        *)
            echo "Usage: $0 [--docker] [start|stop|restart|logs|stream-logs|start-daemon|stop-daemon|logs-daemon|start-daemon-foreground|start-all]"
            echo ""
            echo "Actions:"
            echo "  start       - Start services"
            echo "  stop        - Stop services"
            echo "  restart     - Restart services"
            echo "  logs        - View container logs (past logs only)"
            echo "  stream-logs - Stream container logs in real-time"
            echo "  start-daemon - Start TaskStudio daemon (direct mode, background)"
            echo "  stop-daemon  - Stop TaskStudio daemon (direct mode)"
            echo "  logs-daemon  - Tail daemon log (direct mode)"
            echo "  start-daemon-foreground - Start BOTH server and daemon in foreground (see console output)"
            echo ""
            echo "Environment Variables:"
            echo "  DAEMON_MODE     - Daemon mode: 'adaptive' (default), 'realtime', or 'fixed'"
            echo "  DAEMON_BATCH    - Max tasks per batch (default: 50)"
            echo "  DAEMON_INTERVAL - Polling interval for fixed mode (default: 30s)"
            echo "  HTTP_PORT       - Server port (default: 8080)"
            echo ""
            echo "Examples:"
            echo "  ./run.sh start                    # Start with adaptive polling (recommended)"
            echo "  DAEMON_MODE=realtime ./run.sh start   # Start with real-time processing"
            echo "  DAEMON_MODE=fixed ./run.sh start      # Start with fixed 30s polling"
            ;;
    esac
fi
