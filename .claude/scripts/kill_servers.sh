#!/bin/bash

# Kill processes running on ports 3000 and 8000
echo "Killing processes on ports 3000 and 8000..."

# Kill port 3000
PORT_3000_PID=$(lsof -ti:3000 2>/dev/null)
if [ ! -z "$PORT_3000_PID" ]; then
    echo "Killing process $PORT_3000_PID on port 3000..."
    kill -9 $PORT_3000_PID 2>/dev/null
else
    echo "No process found on port 3000"
fi

# Kill port 8000
PORT_8000_PID=$(lsof -ti:8000 2>/dev/null)
if [ ! -z "$PORT_8000_PID" ]; then
    echo "Killing process $PORT_8000_PID on port 8000..."
    kill -9 $PORT_8000_PID 2>/dev/null
else
    echo "No process found on port 8000"
fi

# Wait a moment
sleep 2

# Verify ports are free
echo "Verifying ports are free..."
lsof -ti:3000 && echo "⚠️  Port 3000 still in use!" || echo "✅ Port 3000 is free"
lsof -ti:8000 && echo "⚠️  Port 8000 still in use!" || echo "✅ Port 8000 is free"