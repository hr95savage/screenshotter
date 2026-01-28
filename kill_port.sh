#!/bin/bash
# Kill processes running on specified ports

if [ $# -eq 0 ]; then
    echo "Usage: $0 <port1> [port2] [port3] ..."
    echo "Example: $0 3000 5000 8000"
    echo ""
    echo "Or use --all to kill all non-system processes on common dev ports"
    exit 1
fi

if [ "$1" = "--all" ]; then
    echo "Killing processes on common development ports..."
    PORTS=(3000 3001 5000 5001 7000 8000 8080 8081 9000 9001 5173 5174)
    for port in "${PORTS[@]}"; do
        PID=$(lsof -ti:$port)
        if [ ! -z "$PID" ]; then
            echo "Killing process on port $port (PID: $PID)"
            kill -9 $PID 2>/dev/null
        fi
    done
    echo "Done!"
    exit 0
fi

for port in "$@"; do
    PID=$(lsof -ti:$port)
    if [ -z "$PID" ]; then
        echo "No process found on port $port"
    else
        echo "Killing process on port $port (PID: $PID)"
        kill -9 $PID 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "  ✓ Successfully killed"
        else
            echo "  ✗ Failed to kill (may require sudo)"
        fi
    fi
done
