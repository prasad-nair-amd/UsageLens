# UsageLens

**SSH-based system usage tracker for monitoring who's using your loaned GPU systems, when, and for how long.**

Built for AMD Field Application Engineers (FAEs) and IT teams who lend expensive GPU systems to customers and need visibility into actual usage — turning "Is the customer even using it?" from a guess into data.

---

## What It Does

UsageLens connects to remote Linux systems via SSH, collects login history, system load, and GPU utilization, then visualizes usage trends over time in a browser dashboard.

**No agent installation needed on target systems — just SSH access.**

### Key Features

- **Login History Tracking** — who logged in, when, and how long (from `last` command)
- **GPU Utilization** — tracks AMD GPU usage over time via `rocm-smi` (NVIDIA via `nvidia-smi`)
- **System Load** — CPU load averages from `uptime`
- **Usage Overview** — per-host doughnut charts showing utilization vs idle time
- **Historical Dashboards** — 1 week to 3 months of trends with heatmaps
- **Three Access Modes**:
  - **Direct SSH** — connect straight to the target
  - **Via Jump Host** — SSH to a bastion, then hop to the target via alias
  - **Via Slurm** — SSH to a Slurm controller, allocate a reserved node via `salloc`, collect data
- **Auto-Polling** — schedule collection every 1–24 hours for hands-off monitoring
- **Collect All** — one-click collection from every configured host
- **Snapshot Browser** — browse and compare any collected data point
- **Copy Configs** — duplicate host setups for quick onboarding

---

## Quick Start

### Prerequisites

- **Windows**: WSL with Python 3.8+ installed
- **Linux / macOS**: Python 3.8+
- SSH access to target systems (identity file or password)

### Install & Run

```bash
git clone https://github.com/prasad-nair-amd/UsageLens.git
cd UsageLens
pip install fastapi uvicorn paramiko pyyaml filelock sse-starlette
```

**Windows:**
```
start.bat
```

**Linux / macOS:**
```bash
chmod +x start.sh
./start.sh
```

**Or run directly:**
```bash
python -m uvicorn backend.server:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

---

## Adding a Host

### Direct SSH
1. Click **+ Add host**
2. Select **Direct SSH** as access mode
3. Enter hostname, port, username, and auth method (identity file or password)
4. Click **Save host** → **Open** → **Test connection**

### Via Jump Host
1. Select **Via Jump Host**
2. Enter jump host SSH details (hostname, username, identity file)
3. Enter the **SSH alias** to reach the target from the jump host (e.g., `gpu-3`)
4. Save and test

### Via Slurm
1. Select **Via Slurm**
2. Enter Slurm controller SSH details
3. Enter your `salloc` command (e.g., `salloc --reservation=my_reservation --exclusive --account=myacct --mem=0`)
4. Add setup commands if needed (e.g., `module load rocm`)
5. Save and test — data is collected from the allocated node, not the controller

---

## Architecture

```
UsageLens/
├── backend/
│   ├── server.py        # FastAPI app — API endpoints + static file serving
│   ├── ssh_client.py    # Paramiko SSH — direct, jump host, and Slurm connections
│   ├── collector.py     # Runs commands, parses output, stores snapshots
│   ├── analytics.py     # Historical aggregation — daily trends, heatmap, user summary
│   └── storage.py       # JSON/YAML file I/O with file locking
├── static/
│   ├── index.html       # Single-page app — host management + dashboard
│   ├── app.js           # Frontend logic — charts, forms, navigation
│   └── style.css        # AMD-themed styling with animations
├── data/                # Auto-created; holds hosts.yaml + usage_data.json
├── pitch/               # Executive pitch deck generator
├── start.bat            # Windows launcher (runs in foreground, Ctrl+C to stop)
├── start.sh             # Linux/macOS launcher
├── stop.sh              # Linux/macOS — stop background server
└── requirements.txt
```

### Data Collection

Each collection runs these built-in commands silently on the target:

| Command | What it provides |
|---|---|
| `who` | Currently logged-in users |
| `uptime` | System load averages |
| `last -w -500` | Login history with session durations |
| `rocm-smi --showuse` | GPU utilization (AMD), falls back to `nvidia-smi` |

You can add extra commands per host (e.g., `df -h`, `sinfo`) — their output appears in the "Raw command output" collapsible section.

### Storage

- **Host configs**: `data/hosts.yaml` (YAML — human-readable)
- **Usage snapshots**: `data/usage_data.json` (JSON — fast parsing)

---

## Dashboard Views

### Landing Page — Usage Overview
Per-host doughnut charts showing **utilization vs idle time** for the selected period (1 week to 3 months). Click any chart to drill into that host.

### Host Operations Page
- **Snapshot Browser** — dropdown of all collected snapshots with login/session counts
- **Snapshot Detail** — stat cards (users, sessions, time spent, load, GPU utilization), time-per-user bar chart, login history table
- **Usage Trends** — logged-in users over time, system load chart, GPU utilization chart, user activity heatmap (hour × date), user summary table

### Collection Progress
Real-time SSE-streamed progress when collecting — shows each step (connecting, running commands, saving) with animated progress bar.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/hosts` | List all hosts (secrets stripped) |
| `POST` | `/api/hosts` | Create or update a host |
| `DELETE` | `/api/hosts/{id}` | Delete host and all its data |
| `POST` | `/api/hosts/{id}/test` | Test SSH connection |
| `POST` | `/api/hosts/{id}/collect` | Collect a snapshot |
| `GET` | `/api/hosts/{id}/collect-stream` | SSE stream with collection progress |
| `POST` | `/api/hosts/{id}/autopoll` | Toggle auto-polling |
| `GET` | `/api/hosts/{id}/history?range=7d` | Historical trends (7d/14d/30d/60d/90d) |
| `GET` | `/api/hosts/{id}/snapshots` | List all snapshots |
| `GET` | `/api/hosts/{id}/snapshot/{ts}` | Single snapshot detail |
| `DELETE` | `/api/hosts/{id}/snapshot/{ts}` | Delete a snapshot |
| `GET` | `/api/dashboard?range=30d` | Overview data for all hosts |

---

## Headless / Scheduled Collection

Collect without the browser open (e.g., via cron or Task Scheduler):

```bash
python -m backend.collector --all
# or for a single host:
python -m backend.collector --host-id <id>
```

This appends to the same `data/usage_data.json` the web UI reads from.

---

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI, Uvicorn |
| SSH | Paramiko |
| Frontend | Vanilla JS, Chart.js |
| Storage | JSON + YAML (no database required) |
| Styling | Custom CSS with AMD theme |

---

## Security Notes

- SSH passwords in `data/hosts.yaml` are stored in **plaintext** — prefer identity file authentication
- `data/` is in `.gitignore` — never commit it
- The API strips passwords before sending host configs to the browser
- This is a local, single-user tool — not designed for multi-tenant deployment

---

## License

Internal AMD tool.
