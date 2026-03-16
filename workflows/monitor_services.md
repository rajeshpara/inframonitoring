# Monitor Services SOP

**Objective**: Periodically check the status of defined systemd services across multiple RHEL hosts over SSH and format the output into a visual HTML dashboard.

## Required Tools
- `tools/ssh_checker.py`: Connects via Python `subprocess` using `ssh -o BatchMode=yes` to execute `systemctl is-active <service>`. It requires passwordless SSH configured and dumps results to `.tmp/status.json`.
- `tools/render_dashboard.py`: Parses the JSON output and generates `index.html` with vanilla CSS glassmorphism styling and auto-refresh meta tags.
- `tools/monitor_loop.sh`: A helper bash script that runs the above two Python scripts in an infinite 5-minute loop.

## Setup Instructions
1. Define the hosts, SSH usernames, and their respective list of services to monitor inside `config.yaml`.
2. Ensure you have network connectivity to the targets and that passwordless SSH is configured for the respective users on the target hosts.
3. Activate the python virtual environment and ensure dependencies are installed via `pip install -r requirements.txt`.

## Execution Overview
To run the monitoring daemon continually:
```bash
chmod +x tools/monitor_loop.sh
./tools/monitor_loop.sh
```

## Troubleshooting & Edge Cases
- **Connection Timed Out**: Verify the host is reachable and firewall rules permit port 22.
- **Permission Denied (publickey)**: The python script does not hang on password prompts due to `BatchMode=yes`. If it fails here, you must ensure your SSH keys are deployed and loaded into the local ssh-agent.
- **Service Not Found**: Ensure the service name listed in `config.yaml` is exactly as it appears in `systemctl` (e.g. `httpd`, not `apache2` if on RHEL).
