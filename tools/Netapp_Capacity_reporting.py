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
    Parses `storage aggregate show-space` tabular output. 
    Returns a list of dicts: [{"Aggregate": X, "Size": Y, "Used": Z, "Available": A, "Used_Percent": B}, ...]
    """
    aggregates = []
    lines = raw_output.strip().split("\n")
    
    # We look for lines that have 5 columns and where the first word doesn't start with a space or hyphen
    for line in lines:
        if not line.strip() or line.startswith('-') or line.startswith(' '):
            continue
        
        parts = line.split()
        if len(parts) == 5 and "%" in parts[4]:
            if parts[0].lower() == "aggregate":
                continue # Header
            # Found an aggregate line
            aggregates.append({
                "Aggregate": parts[0],
                "Size": parts[1],
                "Used": parts[2],
                "Available": parts[3],
                "Used_Percent": parts[4]
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
        if result.returncode == 0:
            return result.stdout, None
        else:
            return None, result.stderr
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
                out, err = run_ssh_cmd(user, host, "storage aggregate show-space")
                
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
