#!/usr/bin/env python3
"""
render_dashboard.py

Reads `.tmp/status.json` and generates a beautiful vanilla CSS static HTML file
at the project root named `index.html`. Now supports dual-status indicators!
"""

import json
import os
import sys
import csv
from datetime import datetime

STORAGE_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "pure_storage_metrics.csv")
NETAPP_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "netapp_storage_metrics.csv")
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", ".tmp", "status.json")
OUTPUT_HTML = os.path.join(os.path.dirname(__file__), "..", "index.html")
STORAGE_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "pure_storage_metrics.csv")

CSS_STYLES = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    :root {
        --bg-color: #0f172a;
        --card-bg: rgba(30, 41, 59, 0.7);
        --card-border: rgba(255, 255, 255, 0.1);
        --text-main: #f8fafc;
        --text-muted: #94a3b8;
        --green-color: #10b981;
        --red-color: #ef4444;
        --yellow-color: #f59e0b;
        --blue-color: #3b82f6;
    }

    * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }

    body {
        font-family: 'Inter', sans-serif;
        background-color: var(--bg-color);
        background-image: 
            radial-gradient(at 0% 0%, hsla(253,16%,7%,1) 0, transparent 50%), 
            radial-gradient(at 50% 0%, hsla(225,39%,30%,0.2) 0, transparent 50%), 
            radial-gradient(at 100% 0%, hsla(339,49%,30%,0.2) 0, transparent 50%);
        color: var(--text-main);
        min-height: 100vh;
        padding: 2rem;
    }

    .container {
        max-width: 1200px;
        margin: 0 auto;
    }

    header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 3rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--card-border);
    }

    h1 {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(to right, #60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .meta-info {
        text-align: right;
        font-size: 0.875rem;
        color: var(--text-muted);
    }

    .last-updated {
        font-weight: 600;
        color: var(--text-main);
        margin-bottom: 0.25rem;
    }

    .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
        gap: 2rem;
    }

    .host-card {
        background: var(--card-bg);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--card-border);
        border-radius: 1rem;
        padding: 1.5rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .host-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 10px 10px -5px rgba(0, 0, 0, 0.1);
        border-color: rgba(255, 255, 255, 0.2);
    }

    .host-header {
        display: flex;
        align-items: center;
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid rgba(255,255,255, 0.05);
    }

    .host-icon {
        background: rgba(59, 130, 246, 0.2);
        color: var(--blue-color);
        width: 40px;
        height: 40px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 1rem;
    }

    .host-title {
        font-size: 1.25rem;
        font-weight: 600;
    }

    .service-list {
        list-style: none;
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .service-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem;
        background: rgba(0,0,0, 0.25);
        border-radius: 0.5rem;
        border: 1px solid transparent;
    }

    .service-info {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .service-name {
        font-family: monospace;
        font-size: 1rem;
        font-weight: 600;
        color: #e2e8f0;
    }
    
    .dual-indicators {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        align-items: flex-end;
    }

    .indicator-row {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    
    .indicator-label {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        font-weight: 600;
    }

    .status-badge {
        display: flex;
        align-items: center;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        min-width: 90px;
        justify-content: center;
    }

    .status-indicator {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 0.5rem;
    }

    /* Status Colors */
    .status-active {
        background: rgba(16, 185, 129, 0.1);
        color: var(--green-color);
        border: 1px solid rgba(16, 185, 129, 0.2);
    }
    .status-active .status-indicator {
        background-color: var(--green-color);
        box-shadow: 0 0 8px var(--green-color);
        animation: pulse-green 2s infinite;
    }

    .status-dead {
        background: rgba(239, 68, 68, 0.1);
        color: var(--red-color);
        border: 1px solid rgba(239, 68, 68, 0.2);
    }
    .status-dead .status-indicator {
        background-color: var(--red-color);
        box-shadow: 0 0 8px var(--red-color);
        animation: pulse-red 2s infinite;
    }

    .status-unknown {
        background: rgba(245, 158, 11, 0.1);
        color: var(--yellow-color);
        border: 1px solid rgba(245, 158, 11, 0.2);
    }
    .status-unknown .status-indicator {
        background-color: var(--yellow-color);
    }
    
    .status-not_configured {
        background: transparent;
        color: var(--text-muted);
        border: 1px dashed var(--text-muted);
    }
    .status-not_configured .status-indicator {
        background-color: var(--text-muted);
    }

    @keyframes pulse-green {
        0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
        100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    @keyframes pulse-red {
        0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
        70% { box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
"""

def parse_storage_csv():
    """Reads the storage metrics CSV to get latest capacity for all unique arrays."""
    data = {}
    if not os.path.exists(STORAGE_CSV_PATH):
        return data
    try:
        with open(STORAGE_CSV_PATH, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("Array Name")
                if name:
                    data[name] = row # The last one read for this name will be the latest
    except Exception as e:
        print(f"Error reading storage CSV: {e}")
    return data

def parse_netapp_csv():
    """Reads the NetApp metrics CSV to get latest aggregates per cluster."""
    data = {}
    if not os.path.exists(NETAPP_CSV_PATH):
        return data
    try:
        with open(NETAPP_CSV_PATH, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cluster = row.get("Cluster Name")
                aggr = row.get("Aggregate")
                if cluster and aggr:
                    if cluster not in data:
                        data[cluster] = {}
                    data[cluster][aggr] = row
    except Exception as e:
        print(f"Error reading NetApp CSV: {e}")
    return data

def get_status_class(raw_status: str) -> tuple:
    s = str(raw_status).lower()
    if s == 'active':
        return 'status-active', 'Running'
    elif s == 'not_configured':
        return 'status-not_configured', 'N/A'
    elif 'error' in s or 'timeout' in s or 'failed' in s or 'inactive' in s or 'dead' in s:
         return 'status-dead', 'Dead'
    else:
        return 'status-unknown', 'Unknown'

def generate_html(data: dict) -> str:
    metadata = data.get("metadata", {})
    hosts = data.get("hosts", {})
    
    title = metadata.get("dashboard_title", "Services Dashboard")
    last_updated_raw = metadata.get("last_updated", "Never")
    
    # Format time nicely
    try:
        dt = datetime.fromisoformat(last_updated_raw)
        last_updated = dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        last_updated = last_updated_raw

    # Build HTML String
    html = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "    <meta charset='UTF-8'>",
        "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        "    <meta http-equiv='refresh' content='300'>",
        f"    <title>{title}</title>",
        CSS_STYLES,
        "</head>",
        "<body>",
        "    <div class='container'>",
        "        <header>",
        f"            <h1>{title}</h1>",
        "            <div class='meta-info'>",
        "                <div class='last-updated'>Last Updated</div>",
        f"                <div>{last_updated}</div>",
        "                <div style='margin-top: 4px; font-size: 0.75rem; opacity: 0.7;'>Auto-refreshes every 5 mins</div>",
        "            </div>",
        "        </header>",
        "        <div class='grid'>"
    ]
    
    # --- PURE STORAGE SECTION ---
    storage_data = parse_storage_csv()
    if storage_data:
        html.extend([
            "            <div style='grid-column: 1/-1; margin-bottom: 2rem; background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 2rem;'>",
            "                <h2 style='font-size: 1.5rem; margin-bottom: 1.5rem; color: #f8fafc; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 0.5rem;'>Pure Arrays</h2>",
            "                <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;'>",
        ])
        
        for array_name, row in storage_data.items():
            # Clean string numbers (e.g. 5.1:1 -> 5.1, 104.3T -> 104.3)
            cap_str = row.get('Capacity', '0T')
            used_str = row.get('Used Space', '0T')
            
            # The user's mock has "X.X to 1 Data Reduction"
            drr_raw = row.get('Data Reduction', '1.0')
            drr_val = ''.join([c for c in drr_raw if c.isdigit() or c == '.'])
            if not drr_val: drr_val = "1.0"
            drr_formatted = f"{drr_val} to 1"

            try:
                cap_val = float(''.join([c for c in cap_str if c.isdigit() or c == '.']))
                used_val = float(''.join([c for c in used_str if c.isdigit() or c == '.']))
                free_val = cap_val - used_val
                if free_val < 0: free_val = 0
                
                # Strip out units to mimic "66.4 / 104.3 T" text gracefully
                unit = ''.join([c for c in cap_str if c.isalpha()])
                if not unit: unit = "T"
            except:
                cap_val, used_val, free_val, unit = 100, 0, 100, "T"

            # Percentage calculation
            percent = 0
            if cap_val > 0:
                percent = int(round((used_val / cap_val) * 100))

            # Color logic based on utilization percentage requirements
            if percent < 75:
                # Green
                color = "rgba(16, 185, 129, 0.9)"
                border = "rgba(16, 185, 129, 1)"
            elif percent >= 75 and percent < 90:
                # Yellow / Orange
                color = "rgba(245, 158, 11, 0.9)"
                border = "rgba(245, 158, 11, 1)"
            else:
                # Red
                color = "rgba(239, 68, 68, 0.9)"
                border = "rgba(239, 68, 68, 1)"

            chart_id = f"chart_{array_name.replace('-', '_')}"

            html.extend([
                "                    <div class='host-card' style='display: flex; flex-direction: column; align-items: center; padding: 1.5rem 1rem;'>",
                # Title part
                f"                       <div style='font-size: 1.1rem; font-weight: 700; color: #f8fafc; margin-bottom: 1.5rem; text-align: center;'>{array_name}</div>",
                
                # Chart area and text blocks side-by-side
                "                       <div style='display: flex; gap: 1.5rem; width: 100%; align-items: center; justify-content: center'>",
                
                # Left side: Chart
                "                           <div style='position: relative; width: 120px; height: 120px;'>",
                f"                               <canvas id='{chart_id}'></canvas>",
                "                               <div style='position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; pointer-events: none;'>",
                f"                                   <div style='font-size: 1.5rem; font-weight: 700; color: #f8fafc; line-height: 1;'>{percent}%</div>",
                "                               </div>",
                "                           </div>",
                
                # Right side: Metrics stacked
                "                           <div style='display: flex; flex-direction: column; align-items: center; gap: 1rem;'>",
                # Used/Total block
                f"                               <div style='display: flex; flex-direction: column; align-items: center;'>",
                # Dynamically size the text if it's too long
                f"                                   <div style='font-size: {'0.85rem' if len(f'{used_val} / {cap_val} {unit}') > 12 else '1.1rem'}; font-weight: 700; color: #f8fafc; white-space: nowrap;'>{used_val} / {cap_val} {unit}</div>",
                "                                   <div style='font-size: 0.7rem; color: #94a3b8;'>Used / Total</div>",
                "                               </div>",
                # Data Reduction block
                f"                               <div style='display: flex; flex-direction: column; align-items: center;'>",
                f"                                   <div style='font-size: 1.1rem; font-weight: 700; color: #f8fafc;'>{drr_formatted}</div>",
                "                                   <div style='font-size: 0.7rem; color: #94a3b8;'>Data Reduction</div>",
                "                               </div>",
                "                           </div>",
                
                "                       </div>",
                "                    </div>",
                "                    <script>",
                f"                       const ctx_{chart_id} = document.getElementById('{chart_id}').getContext('2d');",
                f"                       new Chart(ctx_{chart_id}, {{",
                "                           type: 'doughnut',",
                "                           data: {",
                "                               labels: ['Used', 'Free'],",
                "                               datasets: [{",
                f"                                   data: [{used_val}, {free_val}],",
                f"                                   backgroundColor: ['{color}', 'rgba(255, 255, 255, 0.1)'],",
                f"                                   borderColor: ['{border}', 'rgba(255, 255, 255, 0.1)'],",
                "                                   borderWidth: 1,",
                "                                   hoverOffset: 2",
                "                               }]",
                "                           },",
                "                           options: { ",
                "                               responsive: true, ",
                "                               maintainAspectRatio: true,",
                "                               plugins: { legend: { display: false }, tooltip: { enabled: true } }, ",
                "                               cutout: '75%', ",
                "                               elements: { arc: { borderJoinStyle: 'round' } },",
                "                               layout: { padding: 0 }",
                "                           }",
                "                       });",
                "                    </script>"
            ])

        html.extend([
            "                </div>", # close grid
            "            </div>"   # close container
        ])
    # --- END PURE STORAGE SECTION ---
    
    # --- NETAPP STORAGE SECTION ---
    netapp_data = parse_netapp_csv()
    if netapp_data:
        html.extend([
            "            <div style='grid-column: 1/-1; margin-bottom: 2rem; background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 2rem;'>",
            "                <h2 style='font-size: 1.5rem; margin-bottom: 1.5rem; color: #f8fafc; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 0.5rem;'>NetApp Clusters</h2>",
            "                <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem;'>",
        ])
        
        for cluster_name, aggregates in netapp_data.items():
            html.extend([
                "                    <div class='host-card' style='padding: 1.5rem;'>",
                # Title
                f"                       <div style='font-size: 1.1rem; font-weight: 700; color: #f8fafc; margin-bottom: 1.5rem; text-align: center;'>{cluster_name}</div>",
                "                       <div style='display: flex; flex-direction: column; gap: 1.5rem;'>"
            ])
            
            for aggr_name, row in aggregates.items():
                size = row.get("Size", "0")
                used = row.get("Used", "0")
                used_pct_str = row.get("Used_Percent", "0%")
                
                try:
                    pct_val = int(used_pct_str.replace('%', ''))
                except:
                    pct_val = 0
                
                # Color logic
                if pct_val < 75:
                    bar_bg = "#10b981" # Green
                elif pct_val < 90:
                    bar_bg = "#f59e0b" # Yellow
                else:
                    bar_bg = "#ef4444" # Red
                
                html.extend([
                    "                           <div>",
                    "                               <div style='display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 0.4rem;'>",
                    f"                                   <div style='color: #e2e8f0; font-weight: 600; font-size: 0.9rem;'>{aggr_name}</div>",
                    f"                                   <div style='color: #94a3b8; font-size: 0.75rem;'>{used} / {size} <span style='color: {bar_bg}; font-weight: 700; margin-left: 0.3rem;'>{pct_val}%</span></div>",
                    "                               </div>",
                    "                               <div style='width: 100%; background-color: rgba(255, 255, 255, 0.1); border-radius: 9999px; height: 0.5rem; overflow: hidden;'>",
                    f"                                   <div style='width: {pct_val}%; background-color: {bar_bg}; height: 100%; border-radius: 9999px; transition: width 0.5s ease-in-out;'></div>",
                    "                               </div>",
                    "                           </div>"
                ])
                
            html.extend([
                "                       </div>",
                "                    </div>"
            ])
            
        html.extend([
            "                </div>",
            "            </div>"
        ])
    # --- END NETAPP SECTION ---

    if not hosts:
        html.append("<div style='grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 3rem;'>")
        html.append("   <p>No hosts configured.</p>")
        html.append("</div>")
    else:
        html.extend([
            "            <div style='grid-column: 1/-1; border-top: 2px dashed rgba(255, 255, 255, 0.1); margin: 1rem 0 2rem 0;'></div>",
            "            <div style='grid-column: 1/-1; margin-bottom: 2rem; background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 2rem;'>",
            "                <h2 style='font-size: 1.5rem; margin-bottom: 1.5rem; color: #f8fafc; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 0.5rem;'>Server Hosts</h2>",
            "                <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem;'>",
        ])
        
        for host, services in hosts.items():
            html.append("            <div class='host-card'>")
            html.append("                <div class='host-header'>")
            html.append("                    <div class='host-icon'>")
            html.append("                        <svg width='24' height='24' fill='none' stroke='currentColor' viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'><path stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01'></path></svg>")
            html.append("                    </div>")
            html.append(f"                    <div class='host-title'>{host}</div>")
            html.append("                </div>")
            html.append("                <ul class='service-list'>")
            
            for service, status_obj in services.items():
                # Support backwards compatibility if it's still a raw string somehow
                if isinstance(status_obj, str):
                    os_raw = status_obj
                    app_raw = 'not_configured'
                else:
                    os_raw = status_obj.get('systemd_status', 'unknown')
                    app_raw = status_obj.get('app_status', 'not_configured')
                    
                os_class, os_text = get_status_class(os_raw)
                app_class, app_text = get_status_class(app_raw)
                
                html.append("                    <li class='service-item'>")
                html.append("                        <div class='service-info'>")
                html.append(f"                            <span class='service-name'>{service}</span>")
                html.append("                        </div>")
                
                # The dual indicators area
                html.append("                        <div class='dual-indicators'>")
                
                # OS Metric row
                html.append("                            <div class='indicator-row' title='systemd status: " + str(os_raw).replace("'", '"') + "'>")
                html.append("                                <span class='indicator-label'>System</span>")
                html.append(f"                                <span class='status-badge {os_class}'>")
                html.append("                                    <span class='status-indicator'></span>")
                html.append(f"                                    {os_text}")
                html.append("                                </span>")
                html.append("                            </div>")
                
                # Application Metric row (only show if it's actually configured)
                if app_raw != 'not_configured':
                    html.append("                            <div class='indicator-row' title='App script status: " + str(app_raw).replace("'", '"') + "'>")
                    html.append("                                <span class='indicator-label'>App</span>")
                    html.append(f"                                <span class='status-badge {app_class}'>")
                    html.append("                                    <span class='status-indicator'></span>")
                    html.append(f"                                    {app_text}")
                    html.append("                                </span>")
                    html.append("                            </div>")

                html.append("                        </div>") # end dual-indicators
                html.append("                    </li>")
                
            html.append("                </ul>")
            html.append("            </div>")

        html.extend([
            "                </div>", # close server hosts grid
            "            </div>"   # close server hosts container
        ])

    html.extend([
        "        </div>",
        "    </div>",
        "</body>",
        "</html>"
    ])

    with open(OUTPUT_HTML, "w") as f:
        f.write("\n".join(html))
        
    print(f"Dashboard successfully generated at {OUTPUT_HTML}")

if __name__ == "__main__":
    if not os.path.exists(DATA_PATH):
        print(f"Error: Could not find JSON output at {DATA_PATH}")
        print("Please run ssh_checker.py first.")
        sys.exit(1)
        
    generate_html(json.load(open(DATA_PATH, "r")))
