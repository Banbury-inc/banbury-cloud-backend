# In order to deploy to gcloud


gcloud auth login

gcloud auth configure-docker

deploy to cloud run

do i need to update dockerfile before I do a git commit?
select cloud build option instead of local

test

# Development Environment

## Running the Server

The project includes a `run.sh` script that provides two ways to run the application:

### 1. Direct Mode (default)

Run services directly on your machine:

```bash
# Start Django and Daphne servers
./run.sh start

# Stop running servers
./run.sh stop

# Restart servers
./run.sh restart
```

### 2. Docker Mode

Run services in a Docker container:

```bash
# Build and start container
./run.sh --docker start

# Stop and remove container
./run.sh --docker stop

# Rebuild and restart container
./run.sh --docker restart

# View container logs (past logs only)
./run.sh --docker logs

# Stream container logs in real-time (continuous monitoring)
./run.sh --docker stream-logs
```

### Legacy Commands

These commands can still be used directly if needed:

```bash
# Run Django server
python3 manage.py runserver 0.0.0.0:8080 --noreload

# Run Websocket server
daphne -p 8082 -b 0.0.0.0 core.asgi:application
```

# Websocket endpoints

request file


# Run Tests

To run the test suite:

```bash
# Run all tests
pytest

# Run specific test file
pytest path/to/test_file.py

# Run with verbose output
pytest -v

# Run tests marked as asyncio
pytest -m asyncio
```

Tests use the configuration in pytest.ini, which enables asyncio mode automatically.






