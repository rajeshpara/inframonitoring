#!/usr/bin/env python3
"""
Pure_Capacity_reporting.py

Reads config.yaml, connects to specified storage arrays (like Pure Storage)
via SSH, runs vendor-specific CLI commands to gather capacity metrics,
and appends the results to a CSV file.

Intended to run on a 60-minute schedule.
"""

import os
import sys
import yaml
import subprocess
import csv
from datetime import datetime

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

# Make logs dir if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

CSV_PATH = os.path.join(LOGS_DIR, "pure_storage_metrics.csv")

def load_config(path: str) -> dict:
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error reading config: {e}")
        sys.exit(1)

def run_ssh_cmd(user, host, remote_cmd, timeout=15):
    """Runs SSH command. Note: passwordless SSH must be configured for the Target."""
    ssh_cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=5",
        f"{user}@{host}",
        remote_cmd
    ]
    try:
        result = subprocess.run(
            ssh_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )
        stdout = result.stdout.decode("utf-8", errors="replace").strip()
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        return stdout, stderr
    except subprocess.TimeoutExpired:
         return "", "SSH Execution Timeout"
    except Exception as e:
         return "", str(e)

def parse_pure_capacity(raw_output: str) -> dict:
    """
    Parses `purearray list --space` tabular output. 
    Handles multi-word headers like "Data Reduction".
    Returns: {"Capacity": X, "Used": Y, "Data Reduction": Z}
    """
    data = {"capacity": "Unknown", "used": "Unknown", "drr": "Unknown"}
    
    lines = raw_output.strip().split("\n")
    if len(lines) < 2:
        return data
        
    # The header line, e.g., "Name  Size  Used  Total  Shared  Snapshots  Data Reduction  Used-Thin"
    header_line = lines[0]
    
    # We can't just split() because "Data Reduction" has a space. 
    # But we can find the exact text indexes because it's fixed width or tab separated.
    # An easier robust way is to replace "Data Reduction" with "DataReduction" before splitting.
    header_clean = header_line.replace("Data Reduction", "DataReduction")
    headers = header_clean.split()
    
    # Do the same for the data rows just in case there are awkward spaces, 
    # but data rows shouldn't have spaces within values (e.g., 5.1:1).
    for i in range(1, len(lines)):
        line = lines[i]
        parts = line.split()
        
        # If the array row has exactly the same number of columns as the headers
        if len(parts) == len(headers):
            # Try to extract the specific columns we care about
            if "Size" in headers:
                data["capacity"] = parts[headers.index("Size")]
            if "Total" in headers:
                 data["used"] = parts[headers.index("Total")]
            if "DataReduction" in headers:
                 data["drr"] = parts[headers.index("DataReduction")]
                 
            # Stop after the first valid line
            break

    return data

def main():
    config = load_config(CONFIG_PATH)
    arrays = config.get("storage_arrays", [])
    
    if not arrays:
        print("No storage arrays configured. Exiting.")
        return

    # Ensure CSV exists with Headers
    file_exists = os.path.isfile(CSV_PATH)
    try:
        with open(CSV_PATH, mode="a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(["Timestamp", "Array Name", "Host", "Capacity", "Used Space", "Data Reduction"])
                
            for array in arrays:
                array_type = array.get("type")
                name = array.get("name")
                host = array.get("host")
                user = array.get("user")
                
                print(f"Checking {array_type} array: {name} ({host})")
                
                if array_type == "pure":
                    # Run Pure CLI space checkout
                    out, err = run_ssh_cmd(user, host, "purearray list --space")
                    
                    if not out:
                         print(f"  [!] Failed to collect metrics: {err}")
                         continue
                         
                    parsed = parse_pure_capacity(out)
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    row = [
                        now_str, 
                        name, 
                        host, 
                        parsed["capacity"], 
                        parsed["used"], 
                        parsed["drr"]
                    ]
                    
                    writer.writerow(row)
                    print(f"  [+] Logged Metrics: {parsed['used']} / {parsed['capacity']}")
                else:
                    continue  # skip non-pure arrays

    except Exception as e:
         print(f"Error updating CSV: {e}")

if __name__ == "__main__":
    main()
