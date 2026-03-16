#!/usr/bin/env bash

# monitor_loop.sh
# Infinite loop to run the SSH checks and render the dashboard every 5 minutes.
# Assumes you are running this from a python virtual environment where PyYAML is installed.

# Ensure we're running from the root of the project
cd "$(dirname "$0")/.." || exit 1

# Optional: activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

echo "Starting Service Monitor Daemon..."
echo "Press Ctrl+C to stop."

while true; do
    echo "============================================="
    echo "Time: $(date)"
    
    # 1. Run the checker
    python3 tools/ssh_checker.py
    
    # 2. Render the dashboard
    python3 tools/render_dashboard.py
    
    echo "Sleeping for 60 seconds..."
    sleep 60
done
