#!/bin/bash

# Start Python FastAPI backend
cd python_backend
python main.py &
PYTHON_PID=$!

echo "Python backend started with PID: $PYTHON_PID"
echo "Backend running on http://0.0.0.0:8000"

# Wait for backend to be ready
sleep 2

# Keep script running
wait $PYTHON_PID
