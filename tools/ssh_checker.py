#!/usr/bin/env python3
"""
ssh_checker.py

Reads config.yaml, connects to the specified hosts via SSH, and checks
the 'systemctl is-active' status for their respective defined services.
If an 'app_check_cmd' is provided, it executes that command as well.

Stateful Alerting:
Maintains a counter of consecutive failures in `.tmp/alert_state.json`.
Sends an SMTP email if failures hit the configured threshold.

Outputs a JSON string mapping host -> service -> status to `.tmp/status.json`.
"""

import sys
import yaml
import json
import subprocess
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", ".tmp", "status.json")
STATE_PATH = os.path.join(os.path.dirname(__file__), "..", ".tmp", "alert_state.json")

def load_json(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_config(path: str) -> dict:
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error reading config: {e}")
        sys.exit(1)

def is_failed_status(status_str: str) -> bool:
    """Returns True if the status indicates a problem."""
    s = str(status_str).lower()
    return "error" in s or "failed" in s or "dead" in s or "timeout" in s or "inactive" in s or "unsupported" in s

def send_alert_email(alert_config: dict, host: str, service_name: str, sys_status: str, app_status: str):
    """Dispatches an HTML-formatted SMTP email based on config.yaml alerting section."""
    if not alert_config.get("enabled", False):
        return

    sender = alert_config.get("sender_email")
    recipients = alert_config.get("recipient_emails", [])
    if not sender or not recipients:
         print(f"Alerting skipped for {service_name}: missing email config.")
         return

    msg = EmailMessage()
    msg['Subject'] = f"🚨 [ALERT] {host} - {service_name} is DOWN"
    msg['From'] = sender
    msg['To'] = ", ".join(recipients)
    
    # Fallback plain text
    msg.set_content(
        f"URGENT: Infrastructure Alert\n\n"
        f"Host: {host}\n"
        f"Service: {service_name}\n\n"
        f"Consecutive Failures Threshold Reached!\n\n"
        f"Latest Status:\n"
        f"  - OS/systemd: {sys_status}\n"
        f"  - App Check:  {app_status}\n\n"
        f"Please investigate immediately."
    )

    # HTML Styling
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px; color: #1e293b;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
          <div style="background-color: #ef4444; color: white; padding: 20px; text-align: center;">
            <h2 style="margin: 0; font-size: 24px;">🚨 Critical Infrastructure Alert</h2>
          </div>
          <div style="padding: 24px;">
            <p style="font-size: 16px; margin-top: 0;">A core service has failed consecutive health checks and requires immediate attention.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px; text-align: left;">
              <tr style="border-bottom: 1px solid #e2e8f0;">
                <th style="padding: 12px 0; color: #64748b; font-weight: 600;">Target Host</th>
                <td style="padding: 12px 0; font-weight: bold;">{host}</td>
              </tr>
              <tr style="border-bottom: 1px solid #e2e8f0;">
                <th style="padding: 12px 0; color: #64748b; font-weight: 600;">Failing Service</th>
                <td style="padding: 12px 0; font-weight: bold; color: #ef4444;">{service_name}</td>
              </tr>
              <tr style="border-bottom: 1px solid #e2e8f0;">
                 <th style="padding: 12px 0; color: #64748b; font-weight: 600;">Systemd Status</th>
                 <td style="padding: 12px 0; font-family: monospace;">{sys_status}</td>
              </tr>
              <tr style="border-bottom: 1px solid #e2e8f0;">
                 <th style="padding: 12px 0; color: #64748b; font-weight: 600;">App-Level Check</th>
                 <td style="padding: 12px 0; font-family: monospace;">{app_status}</td>
              </tr>
            </table>

            <div style="margin-top: 24px; text-align: center;">
               <p style="color: #64748b; font-size: 14px;">Automated alert from your WAT Monitoring Agent</p>
            </div>
          </div>
        </div>
      </body>
    </html>
    """
    
    msg.add_alternative(html_content, subtype='html')

    try:
        server = smtplib.SMTP(
            alert_config.get("smtp_server", "localhost"), 
            alert_config.get("smtp_port", 25)
        )
        if alert_config.get("use_tls", False):
            server.starttls()
            
        password = alert_config.get("sender_password")
        if password:
            server.login(sender, password)
            
        server.send_message(msg)
        server.quit()
        print(f"  [!] Beautiful HTML Alert EMAIL SENT to {len(recipients)} recipients.")
    except Exception as e:
        print(f"  [!] Failed to send alert email: {e}")

def run_ssh_cmd(user: str, host: str, remote_cmd: str, timeout: int) -> tuple[str, str]:
    """Runs an arbitrary SSH command and returns (stdout, stderr). Raises TimeoutExpired."""
    ssh_cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=5",
        f"{user}@{host}",
        remote_cmd
    ]
    result = subprocess.run(
        ssh_cmd, 
        capture_output=True, 
        text=True, 
        timeout=timeout
    )
    return result.stdout.strip(), result.stderr.strip()

def check_service(user: str, host: str, service_name: str, app_cmd: str | None, timeout: int) -> dict[str, str]:
    """
    Checks the status of the systemd service, and optionally runs an app-level check.
    Returns a dict with 'systemd_status' and 'app_status'.
    """
    status_dict = {
        "systemd_status": "unknown",
        "app_status": "not_configured" if not app_cmd else "unknown"
    }

    # 1. Check systemd process state
    try:
        sys_out, sys_err = run_ssh_cmd(user, host, f"systemctl is-active {service_name}", timeout)
        if not sys_out:
            if "Permission denied" in sys_err:
                status_dict["systemd_status"] = "ssh_auth_error"
                status_dict["app_status"] = "ssh_auth_error" if app_cmd else "not_configured"
                return status_dict
            if "Connection timed out" in sys_err or "Connection refused" in sys_err or "No route to host" in sys_err:
                status_dict["systemd_status"] = "error: " + sys_err
                status_dict["app_status"] = ("error: " + sys_err) if app_cmd else "not_configured"
                return status_dict
            if "command not found" in sys_err.lower():
                 status_dict["systemd_status"] = "os_unsupported"
            else:
                 status_dict["systemd_status"] = "error: " + sys_err
        else:
            status_dict["systemd_status"] = sys_out

    except subprocess.TimeoutExpired:
        status_dict["systemd_status"] = "timeout"
        status_dict["app_status"] = "timeout" if app_cmd else "not_configured"
        return status_dict
    except Exception as e:
        status_dict["systemd_status"] = f"error: {e}"
        status_dict["app_status"] = f"error: {e}" if app_cmd else "not_configured"
        return status_dict

    # 2. Check application state (if configured and systemd didn't entirely fail SSH connection)
    if app_cmd and "error" not in status_dict["systemd_status"] and "timeout" not in status_dict["systemd_status"]:
        try:
            timeout_cmd = f"timeout {timeout} {app_cmd}"
            app_out, app_err = run_ssh_cmd(user, host, timeout_cmd, timeout+2)
            
            if app_err and not app_out:
                status_dict["app_status"] = "failed"
            elif not app_out and not app_err: 
                 status_dict["app_status"] = "active"
            else:
                output = app_out if app_out else app_err
                status_dict["app_status"] = "active" if "failed" not in output.lower() and "error" not in output.lower() else "failed"
                
        except Exception as e:
             status_dict["app_status"] = f"error: {e}"

    return status_dict

def main():
    config = load_config(CONFIG_PATH)
    targets = config.get("targets", [])
    settings = config.get("settings", {})
    alert_config = settings.get("alerting", {})
    
    timeout = settings.get("timeout_seconds", 10)
    alert_threshold = alert_config.get("consecutive_failures_to_alert", 3)
    
    # Load previous alert state (fail counts)
    state = load_json(STATE_PATH)

    results = {
        "metadata": {
            "last_updated": datetime.now().isoformat(),
            "dashboard_title": settings.get("dashboard_title", "Monitoring Dashboard")
        },
        "hosts": {}
    }

    print("Starting SSH service checks...")
    for target in targets:
        host = target.get("host")
        user = target.get("user")
        services = target.get("services", [])
        
        # Ensure state dict memory exists for this host
        if host not in state:
            state[host] = {}
            
        print(f"Checking {host} (user: {user})...")
        results["hosts"][host] = {}
        
        for svc in services:
            # Handle list strings or object dictionaries
            if isinstance(svc, dict):
                service_name = str(svc.get("name", "unknown"))
                app_cmd = svc.get("app_check_cmd")
                if app_cmd is not None:
                     app_cmd = str(app_cmd)
            else:
                service_name = str(svc)
                app_cmd = None
                
            print(f"  -> {service_name}: ", end="")
            status_obj = check_service(user, host, service_name, app_cmd, timeout)
            
            s_sys = status_obj['systemd_status']
            s_app = status_obj['app_status']
            
            print(f"OS=[{s_sys}] App=[{s_app}]")
            
            # STATE TRACKING AND ALERTING LOGIC
            is_down = is_failed_status(s_sys) or is_failed_status(s_app)
            
            if service_name not in state[host]:
                state[host][service_name] = {"failures": 0, "alert_sent": False}
                
            service_state = state[host][service_name]
            
            if is_down:
                service_state["failures"] += 1
                fails = service_state["failures"]
                
                print(f"     [!] Consecutive failures: {fails}/{alert_threshold}")
                
                # Check if we should alert
                if fails >= alert_threshold and not service_state["alert_sent"]:
                    print(f"     [*] Threshold reached. Triggering alert...")
                    send_alert_email(alert_config, host, service_name, s_sys, s_app)
                    service_state["alert_sent"] = True # Prevent spam in future runs
                    
            else:
                # Service is healthy, reset memory
                if service_state["failures"] > 0:
                    print(f"     [+] Service recovered. Resetting failure counter.")
                service_state["failures"] = 0
                service_state["alert_sent"] = False
            
            # Save results into memory
            results["hosts"][host][service_name] = status_obj

    # Write output AND updated state
    save_json(OUTPUT_PATH, results)
    save_json(STATE_PATH, state)
        
    print(f"Checks completed. Results written to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
