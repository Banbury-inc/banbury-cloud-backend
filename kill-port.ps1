# PowerShell script to kill process on a specific port
param(
    [int]$Port = 8080
)

Write-Host "Checking for processes using port $Port..."

# Get the process ID using the port
$connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue

if ($connection) {
    $pid = $connection.OwningProcess
    $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
    
    if ($process) {
        Write-Host "Found process: $($process.ProcessName) (PID: $pid)"
        Write-Host "Killing process..."
        
        try {
            Stop-Process -Id $pid -Force
            Write-Host "Successfully killed process on port $Port"
            
            # Wait a moment for the port to be released
            Start-Sleep -Seconds 2
            
            # Verify port is free
            $check = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
            if (-not $check) {
                Write-Host "Port $Port is now free" -ForegroundColor Green
            } else {
                Write-Host "Warning: Port $Port may still be in use" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "Error killing process: $_" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Process with PID $pid not found"
    }
} else {
    Write-Host "No process found using port $Port" -ForegroundColor Green
}
