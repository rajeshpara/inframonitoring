#!/usr/bin/env python3
"""
Netapp_Capacity_reporting.py

Reads config.yaml, connects to specified NetApp storage arrays via SSH, 
runs vendor-specific CLI commands to gather aggregate capacity metrics,
and appends them to logs/netapp_storage_metrics.csv.
"""

import yaml
import subprocess
import os
import csv
from datetime import datetime

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "netapp_storage_metrics.csv")

def extract_netapp_aggregates(raw_output: str) -> list:
    """
    Parses output of:
      storage aggregate show -fields size,usedsize,availsize,percent-used

    The header row defines column order; values are read positionally so the
    output remains correct regardless of column ordering.

    Returns a list of dicts:
      [{"Aggregate": X, "Size": Y, "Used": Z, "Available": A, "Used_Percent": B}, ...]
    """
    aggregates = []
    lines = raw_output.strip().split("\n")

    # Map NetApp field names → our CSV keys
    FIELD_MAP = {
        "aggregate": "Aggregate",
        "size":      "Size",
        "usedsize":  "Used",
        "availsize": "Available",
        "percent-used": "Used_Percent",
    }

    headers = None  # list of our CSV keys in column order

    for line in lines:
        stripped = line.strip()

        # Skip blank lines, separator lines, footer, and login banner
        if (not stripped
                or stripped.startswith("-")
                or "entries were displayed" in stripped
                or stripped.startswith("Last login")):
            continue

        parts = stripped.split()

        # Detect header row by presence of known field names
        if headers is None and parts[0].lower() in FIELD_MAP:
            headers = [FIELD_MAP.get(p.lower(), p) for p in parts]
            continue

        if headers is None:
            continue  # still looking for the header

        if len(parts) < len(headers):
            continue  # malformed line

        row = dict(zip(headers, parts))
        aggregates.append({
            "Aggregate":   row.get("Aggregate", "N/A"),
            "Size":        row.get("Size", "N/A"),
            "Used":        row.get("Used", "N/A"),
            "Available":   row.get("Available", "N/A"),
            "Used_Percent": row.get("Used_Percent", "N/A"),
        })

    return aggregates

def run_ssh_cmd(user, host, command, timeout=20):
    try:
        ssh_cmd = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=5",
            "-o", "StrictHostKeyChecking=no",
            f"{user}@{host}",
            command
        ]
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
        # NetApp SSH sessions often return a non-zero exit code even on success.
        # Treat any non-empty stdout as success.
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        # NetApp may send output to stderr; use whichever stream has content
        output = stdout or stderr
        if output:
            return output, None
        else:
            return None, f"Empty output (exit code {result.returncode})"
    except Exception as e:
        return None, str(e)

def main():
    try:
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading {CONFIG_PATH}: {e}")
        return

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    
    file_exists = os.path.exists(LOG_PATH)
    
    with open(LOG_PATH, "a", newline="") as csvfile:
        fieldnames = ["Timestamp", "Cluster Name", "Host", "Aggregate", "Size", "Used", "Available", "Used_Percent"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
            
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        arrays = config.get("storage_arrays", [])
        for array in arrays:
            array_type = array.get("type", "").lower()
            name = array.get("name", "unknown")
            host = array.get("host", "unknown")
            user = array.get("user", "admin")
            
            if array_type == "netapp":
                print(f"Checking NetApp array: {name} ({host})")
                out, err = run_ssh_cmd(user, host, "storage aggregate show -fields size,usedsize,availsize,percent-used")
                
                if not out:
                     print(f"  [!] Failed to collect metrics: {err}")
                     continue
                     
                aggregates = extract_netapp_aggregates(out)
                if not aggregates:
                     print(f"  [!] No aggregates parsed from output.")
                     continue
                     
                for aggr in aggregates:
                    writer.writerow({
                        "Timestamp": current_time,
                        "Cluster Name": name,
                        "Host": host,
                        "Aggregate": aggr["Aggregate"],
                        "Size": aggr["Size"],
                        "Used": aggr["Used"],
                        "Available": aggr["Available"],
                        "Used_Percent": aggr["Used_Percent"]
                    })
                print(f"  [+] Logged {len(aggregates)} aggregates.")

if __name__ == "__main__":
    main()
