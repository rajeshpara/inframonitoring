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

first_run=true
last_run_hour=""

while true; do
    echo "============================================="
    current_time=$(date)
    current_min=$(date +%M)
    current_hour=$(date +%H)
    
    echo "Time: $current_time"
    
    # Run storage checker on first run OR exactly at the top of the hour (minute 00)
    # The last_run_hour check prevents it from running multiple loops within the 00 minute window
    if [ "$first_run" = true ] || { [ "$current_min" = "00" ] && [ "$last_run_hour" != "$current_hour" ]; }; then
        echo "Running storage metrics collection..."
        python3 tools/Pure_Capacity_reporting.py
        python3 tools/Netapp_Capacity_reporting.py
        first_run=false
        last_run_hour=$current_hour
    fi
    
    # 1. Run the service checker
    python3 tools/ssh_checker.py
    
    # 2. Render the dashboard
    python3 tools/render_dashboard.py
    
    echo "Sleeping for 60 seconds..."
    sleep 60
done
