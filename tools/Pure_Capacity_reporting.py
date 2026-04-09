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

    Splits both header and data rows by 2+ consecutive spaces so that
    multi-word column names ("Data Reduction", "Thin Provisioning") and
    multi-word values ("1.8 to 1") are preserved as single tokens.

    Extracts: Capacity, Total (used), Data Reduction ratio.
    """
    import re

    data = {"capacity": "Unknown", "used": "Unknown", "drr": "Unknown"}

    lines = [l for l in raw_output.strip().split("\n") if l.strip()]
    if len(lines) < 2:
        return data

    headers = [h.strip() for h in re.split(r'\s{2,}', lines[0].strip())]

    for line in lines[1:]:
        if not line.strip():
            continue
        values = [v.strip() for v in re.split(r'\s{2,}', line.strip())]
        if len(values) != len(headers):
            continue
        row = dict(zip(headers, values))
        data["capacity"] = row.get("Capacity", "Unknown")
        data["used"]     = row.get("Total", "Unknown")
        data["drr"]      = row.get("Data Reduction", "Unknown")
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
                
                if array_type == "pure":
                    print(f"Checking pure array: {name} ({host})")
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
