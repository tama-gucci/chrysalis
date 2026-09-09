# 🛰️ Ambient Chrysalis Gateway

The **Ambient Chrysalis Gateway** is a lightweight, asynchronous Python FastAPI daemon designed to run 24/7 on your home server ("Golem" — Microsoft Surface Pro X on Windows 11 ARM64). It exposes high-throughput, low-latency REST and bidirectional WebSocket interfaces bridging the Chrysalis Mobile and Wear OS clients to autonomous agent orchestrators via a **Pluggable Orchestrator Bridge**.

---

## 🏛️ Architecture & Port Separation Invariant

### 1. The Port Separation Invariant (Port 8765 vs Port 8080)
To ensure seamless coexistence with the desktop Obsidian environment:
* **Port `8080`:** Reserved exclusively for the **Obsidian TaskNotes plugin API** and local server.
* **Port `8765`:** Dedicated to the **Ambient Chrysalis Gateway daemon**.
* *Both services run side-by-side on Golem without port collision.*

### 2. The Single-Install Invariant (Zero-Phone-Config)
> *The Chrysalis Android app and Wear OS watch must be the ONLY pieces of software installed on client devices. No auxiliary VPN apps (WireGuard/Tailscale), no secondary sync daemons, and no mobile terminal emulators.*

To achieve secure global remote access with zero open router ports:
1. **At-Home Daemon:** The FastAPI gateway runs locally on `0.0.0.0:8765`.
2. **Cloudflare Zero-Trust Tunnel:** An outbound-only tunnel (`cloudflared`) connects the local gateway to a secure public hostname (e.g. `https://gateway.example.com`).
3. **Client Access:** Chrysalis Mobile and Wear OS make standard HTTPS and WSS requests over TLS using Bearer token authentication.

```
┌───────────────────────────┐       HTTPS / WSS        ┌───────────────────────┐
│ Chrysalis Mobile & Watch  │ ───────────────────────> │ Cloudflare Edge       │
│ (Flutter / Wear OS OLED)  │  Bearer Token Auth       │ (Zero Open Ports)     │
└───────────────────────────┘                          └──────────┬────────────┘
                                                                  │ Outbound Tunnel
                                                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ "Golem" Home Server (Surface Pro X - Windows 11 on ARM64 - 16GB Total RAM)  │
│                                                                             │
│  ┌───────────────────────────────┐      ┌────────────────────────────────┐  │
│  │ Hyper-V: Home Assistant (4GB) │      │ Obsidian TaskNotes (Port 8080) │  │
│  └───────────────────────────────┘      └────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────┐      ┌────────────────────────────────┐  │
│  │ cloudflared Tunnel Service    │ ───> │ Ambient Gateway (Port 8765)   │  │
│  └───────────────────────────────┘      └───────────────┬────────────────┘  │
│                                                         │                   │
│                                                         ▼                   │
│                                         ┌────────────────────────────────┐  │
│                                         │ Pluggable Orchestrator Bridge  │  │
│                                         │ (BaseOrchestratorBridge)       │  │
│                                         └───────┬───────────┬────────────┘  │
│                                                 │           │               │
│                      ┌──────────────────────────┘           └────────┐      │
│                      ▼                                               ▼      │
│     ┌───────────────────────────────────┐               ┌────────────────┐  │
│     │ Antigravity Language Server (Ref) │               │ OpenClaw /     │  │
│     │ (language_server.exe / agentapi)  │               │ Hermes OS / LLM│  │
│     └───────────────────────────────────┘               └────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔌 Pluggable Orchestrator Bridge Architecture

The gateway decouples network transport from agent orchestration through the `BaseOrchestratorBridge` adapter interface ([`orchestrator_bridge.py`](orchestrator_bridge.py)):

* **`AntigravityBridge` (Reference Implementation):** Connects to the local Google Antigravity language server via `language_server.exe agentapi` or `agentapi.bat` on Windows (`~/.gemini/antigravity/bin/agentapi` on POSIX). Dispatches slash commands (`/morning`, `/evening`, `/plan`, `/task`, `/zettel`, `/doctor`, `/audit`, `/pause`) and streams markdown responses.
* **`OpenClawBridge` (Pluggable Slot):** Direct bridge for OpenClaw-based autonomous agent execution.
* **`HermesOSBridge` (Pluggable Slot):** Direct bridge for Hermes OS / local LLM inference engines.

---

## 📡 API Specification

### 1. `POST /api/orchestrator/command`
Dispatches a Chrysalis slash command or conversational prompt to the active orchestrator.

**Request:**
```json
{
  "command": "/morning",
  "args": {
    "wake": "07:45",
    "energy": 4
  },
  "conversation_id": "optional-existing-conversation-id",
  "model": "flash"
}
```

**Response:**
```json
{
  "success": true,
  "command": "/morning",
  "output": "🌅 Morning Calibration Completed\n- Wake time locked: 07:45...",
  "conversation_id": "auto-created-or-passed-id",
  "execution_time_ms": 240,
  "timestamp": "2026-09-09T07:45:00-05:00"
}
```

### 2. `GET /api/orchestrator/status`
Returns real-time health, uptime, active profile, and availability of the orchestrator bridge.

**Response:**
```json
{
  "status": "online",
  "orchestrator": "antigravity",
  "agentapi_available": true,
  "agentapi_path": "C:\\Users\\user\\AppData\\Local\\Programs\\antigravity\\resources\\bin\\language_server.exe",
  "uptime_seconds": 3600.0,
  "active_profile": "station-node",
  "port": 8765,
  "version": "1.0.0",
  "emulation_mode": false,
  "timestamp": "2026-09-09T07:45:00-05:00"
}
```

### 3. `WebSocket /api/orchestrator/ws`
Bidirectional streaming connection for real-time interactive chat, voice transcription playback, and task generation.

- **Client Ping:** `{"type": "ping"}` $\to$ **Server Pong:** `{"type": "pong", "timestamp": "..."}`
- **Client Command:** `{"type": "command", "command": "/plan", "args": {}}`
- **Server Stream:**
  - `{"type": "chunk", "data": "Dispatching command: /plan..."}`
  - `{"type": "complete", "success": true, "data": {...}}`

---

## 🚀 Setup on "Golem" (Surface Pro X - Windows 11 on ARM64)

### 1. Python Environment Setup (PowerShell)
```powershell
cd "apps\gateway"

# Create a clean Windows venv and install dependencies
Remove-Item -Recurse -Force .venv -ErrorAction SilentlyContinue
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Launching Gateway Locally
```powershell
$env:CHRYSALIS_GATEWAY_HOST = "0.0.0.0"
$env:CHRYSALIS_GATEWAY_PORT = "8765"
$env:CHRYSALIS_GATEWAY_TOKEN = "generate-a-secure-random-token"
python main.py
```

Verify in browser:
```text
http://localhost:8765/health
```
Response: `{"status": "healthy", "service": "ambient-chrysalis-gateway", "version": "1.0.0"}`

### 3. Cloudflare Zero-Trust Tunnel Setup (Windows Service)
1. Install `cloudflared` on Windows:
   ```powershell
   winget install --id Cloudflare.cloudflared
   cloudflared tunnel login
   ```
2. Create your tunnel:
   ```powershell
   cloudflared tunnel create chrysalis-gateway
   ```
3. Configure `config.yml` (point service to `http://localhost:8765`):
   ```yaml
   tunnel: <TUNNEL-UUID>
   credentials-file: C:\Users\<user>\.cloudflared\<TUNNEL-UUID>.json

   ingress:
     - hostname: gateway.yourdomain.com
       service: http://localhost:8765
     - service: http_status:404
   ```
4. Install and start as a 24/7 background Windows Service:
   ```powershell
   cloudflared tunnel route dns chrysalis-gateway gateway.yourdomain.com
   cloudflared service install
   Start-Service cloudflared
   ```

---

## 🐧 Linux / POSIX Deployment (Alternative)

If hosting the gateway on a Linux server:

```bash
cd apps/gateway
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8765
```

Systemd unit template is provided in `cloudflare/chrysalis-gateway.service.template`.

---

## 🔒 Security Configuration

- **Bearer Token Authentication:** Set `CHRYALIS_GATEWAY_TOKEN="your-secret-token"`. All REST requests must pass `Authorization: Bearer your-secret-token`, and WebSocket connections must pass `?token=your-secret-token`.
- **Cloudflare Zero-Trust:** Access can be protected with Cloudflare Access policies, service tokens, or client certificates.
