# Ambient gateway prototype

Optional FastAPI transport connecting Chrysalis clients to an external Antigravity executable. It is not required for interactive Markdown-based life operations.

## Run locally

Create an isolated Python environment and install `requirements.txt`. From this directory:

```powershell
python main.py
```

The default listener is `127.0.0.1:8765`; Obsidian uses port 8080. Configure `CHRYSALIS_AGENTAPI_PATH` for the executable and `CHRYSALIS_GATEWAY_TOKEN` for authenticated requests. Use an explicit host setting when deliberately exposing the service beyond loopback.

`/health` checks the HTTP service. `/api/orchestrator/status` reports backend availability separately. A healthy HTTP server does not mean an agent can execute commands.

## Execution behavior

A missing Antigravity executable returns an unavailable error. Emulation requires `CHRYSALIS_EMULATION_MODE=true`, labels every response as simulation, and changes no vault files. OpenClaw and Hermes adapters are reserved interfaces and return unavailable.

The Antigravity process adapter remains a prototype: verify installed CLI compatibility and the intended vault context before relying on unattended operations. Cloudflare files are configuration templates, not proof of a deployed tunnel. Windows installer packaging is planned.

## Tests

```powershell
python -m pytest tests -q
```

Tests explicitly enable simulation and never launch the user's real agent. Additional tests cover absent backends, visible simulation, authentication, and malformed WebSocket input.
