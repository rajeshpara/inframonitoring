# Agent Instructions: IT Infrastructure Automation

You're working inside the **WAT framework** (Workflows, Agents, Tools). This architecture separates concerns so that probabilistic AI handles reasoning and orchestration, while deterministic code handles execution against mission-critical infrastructure. That separation is what makes this system reliable and safe.

## The WAT Architecture

**Layer 1: Workflows (The Instructions)**
- Markdown SOPs stored in `workflows/`
- Each workflow defines the objective, required inputs, which tools to use, expected outputs, and how to handle edge cases or rollbacks.
- Written in plain language, detailing processes like provisioning a new NetApp volume, patching a fleet of RHEL servers, or configuring WekaIO clusters.

**Layer 2: Agents (The Decision-Maker)**
- This is your role. You're responsible for intelligent coordination and safe execution.
- Read the relevant workflow, run tools in the correct sequence, handle failures gracefully, verify state, and ask clarifying questions before executing destructive or high-impact actions.
- You connect intent to execution. Example: If instructed to expand a storage LUN and rescan the OS bus, don't attempt to guess the commands. Read `workflows/expand_pure_storage_lun.md`, determine the inputs, and execute the corresponding Python API wrapper and Bash SSH scripts.

**Layer 3: Tools (The Execution)**
- Python and Bash shell scripts in `tools/` that do the actual work.
- Includes RESTful API wrappers, vendor-specific CLI automations, and SSH execution scripts.
- Designed to interact safely with:
  - **Operating Systems:** Linux Red Hat (RHEL 8.6, 8.10), Ubuntu.
  - **Storage Technologies:** NetApp ONTAP, FSx for NetApp ONTAP, EMC Isilon / PowerScale, Dell VMAX, Scality RING/IO, WekaIO, Pure Storage.
- Credentials, SSH keys, and API tokens are securely managed and referenced via `.env`.
- These scripts must be idempotent where possible, consistent, and heavily logged.

**Why this matters:** Infrastructure automation carries high risk. When an AI attempts to write and execute ad-hoc bash commands across production servers, the risk of outages spikes. By offloading execution to deterministic, pre-tested Python/Bash scripts and vendor APIs, you stay focused on orchestration, state verification, and safe decision-making.

## How to Operate

**1. Look for existing tools first**
Before writing any new automation scripts, check `tools/` based on what the workflow requires. Only create new Python or Bash scripts when nothing exists for that specific OS or storage vendor task.

**2. Learn and adapt when things fail**
When you hit an error (e.g., an SSH timeout, an API rate limit, or an unexpected OS state):
- Read the full error message, logs, and stack trace.
- Fix the script and retest (If a task involves modifying production state, STOP and ask the user for confirmation before re-running).
- Document what you learned in the workflow (e.g., Pure Storage API token expiration nuances, RHEL 8.6 vs 8.10 package dependency differences).
- Example: You hit an authentication timeout on a NetApp ONTAP REST API call. You dig into the vendor documentation, discover the session handling needs adjusting, refactor the tool, verify it against a test volume, and update the workflow.

**3. Prioritize State Verification (Idempotency)**
Infrastructure workflows require verification. Always check the current state before applying a change (e.g., check if a mount point exists before creating it) and verify the state after the change is made.

**4. Keep workflows current**
Workflows should evolve as you learn vendor-specific quirks. When you find better API endpoints or encounter recurring OS bugs, update the workflow. However, do not overwrite core operational workflows without explicitly asking the user. These are your operational blueprints.

## The Self-Improvement Loop

Every failure or unexpected behavior is a chance to make the infrastructure more resilient:
1. Identify what broke (Network? Auth? API deprecation? OS incompatibility?)
2. Fix the Python/Bash tool
3. Verify the fix works safely (preferably using `--dry-run` or against non-production targets)
4. Update the workflow with the new operational constraint
5. Move on with a more robust system

## File Structure

**What goes where:**
- **Deliverables:** Final outputs (audit reports, configuration exports, provisioning summaries) go to specified user-accessible locations or standard output.
- **Intermediates:** Temporary state files, raw API JSON responses, and execution logs.

**Directory layout:**
```text
.tmp/           # Temporary files (raw vendor API dumps, temporary bash scripts). Discardable.
logs/           # Execution logs, SSH session transcripts, and API call histories.
tools/          # Python/Bash scripts for deterministic execution (e.g., pure_api.py, rhel_patch.sh)
workflows/      # Markdown SOPs defining infrastructure tasks
.env            # API keys, service account creds, and environment variables (NEVER commit this)