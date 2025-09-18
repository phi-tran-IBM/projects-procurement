#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "🚀 Starting Test Suite..."

# Start the Flask server in the background
echo "🔥 Starting Flask server in the background..."
python app.py > app_server.log 2>&1 &
# Get the process ID of the background server
SERVER_PID=$!
echo "Server started with PID: $SERVER_PID"

# Wait for the server to initialize
echo "⏳ Waiting for server to initialize (5 seconds)..."
sleep 5

# Check if the server is running
if ! ps -p $SERVER_PID > /dev/null; then
    echo "❌ Server failed to start. Check app_server.log for details."
    exit 1
fi

echo "✅ Server is running."

# Run the tests
echo "▶️ Running unit tests (test_downstream_logic.py)..."
python test_downstream_logic.py

echo "▶️ Running integration tests (run_tests_detailed.py)..."
python run_tests_detailed.py

echo "▶️ Running API tests (test_running_api.py)..."
python test_running_api.py

# Kill the server process after tests are complete
echo "🛑 Stopping Flask server..."
kill $SERVER_PID
echo "✅ Server stopped."

echo "✨ Test Suite Finished. ✨"
