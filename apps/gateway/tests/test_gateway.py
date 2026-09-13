import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add apps/gateway to path so imports work cleanly
gateway_dir = Path(__file__).resolve().parent.parent
if str(gateway_dir) not in sys.path:
    sys.path.insert(0, str(gateway_dir))

from config import config
from main import app
from orchestrator_bridge import orchestrator_bridge

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_gateway(monkeypatch):
    # API tests must never launch the user's real orchestrator.
    monkeypatch.setattr(config, "EMULATION_MODE", True)
    monkeypatch.setattr(config, "AUTH_TOKEN", None)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ambient-chrysalis-gateway"
    assert "version" in data

def test_get_orchestrator_status():
    response = client.get("/api/orchestrator/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "simulation"
    assert "uptime_seconds" in data
    assert "active_profile" in data
    assert "agentapi_available" in data

def test_execute_morning_command():
    payload = {
        "command": "/morning",
        "args": {"wake": "08:15", "energy": 4},
        "model": "flash"
    }
    response = client.post("/api/orchestrator/command", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["command"] == "/morning"
    assert "output" in data
    assert data["execution_time_ms"] >= 0
    assert "timestamp" in data

def test_execute_doctor_command():
    payload = {"command": "/doctor"}
    response = client.post("/api/orchestrator/command", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["command"] == "/doctor"
    assert "output" in data

def test_execute_pause_command():
    payload = {
        "command": "/pause",
        "args": {"mode": "rest"}
    }
    response = client.post("/api/orchestrator/command", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "/pause" in data["command"]

def test_websocket_orchestrator_flow():
    with client.websocket_connect("/api/orchestrator/ws") as websocket:
        # 1. Server emits initial status frame on connect
        initial_frame = websocket.receive_json()
        assert initial_frame["type"] == "status"
        assert initial_frame["data"]["status"] == "simulation"

        # 2. Client ping -> Server pong
        websocket.send_json({"type": "ping"})
        pong_frame = websocket.receive_json()
        assert pong_frame["type"] == "pong"
        assert "timestamp" in pong_frame

        # 3. Client requests status
        websocket.send_json({"type": "status"})
        status_frame = websocket.receive_json()
        assert status_frame["type"] == "status"
        assert "data" in status_frame

        # 4. Client dispatches command
        websocket.send_json({
            "type": "command",
            "command": "/plan",
            "args": {"mode": "staging"}
        })

        # Expect chunk frame
        chunk_frame = websocket.receive_json()
        assert chunk_frame["type"] == "chunk"
        assert "Dispatching command" in chunk_frame["data"]
        assert "Dispatching command" in chunk_frame["content"]

        # Expect completion frame
        complete_frame = websocket.receive_json()
        assert complete_frame["type"] == "complete"
        assert complete_frame["success"] is True
        assert "data" in complete_frame
        assert "content" in complete_frame
        assert "metadata" in complete_frame

def test_command_with_parameters_alias():
    payload = {
        "command": "/morning",
        "parameters": {"wake": "08:30", "energy": 5},
    }
    response = client.post("/api/orchestrator/command", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["command"] == "/morning"

def test_token_authentication(monkeypatch):
    monkeypatch.setattr(config, "AUTH_TOKEN", "super-secret-token")

    # Unauthenticated request should return 401
    unauth_resp = client.get("/api/orchestrator/status")
    assert unauth_resp.status_code == 401

    # Request with invalid token should return 401
    bad_resp = client.get(
        "/api/orchestrator/status",
        headers={"Authorization": "Bearer wrong-token"}
    )
    assert bad_resp.status_code == 401

    # Request with valid token should succeed
    auth_resp = client.get(
        "/api/orchestrator/status",
        headers={"Authorization": "Bearer super-secret-token"}
    )
    assert auth_resp.status_code == 200
    assert auth_resp.json()["status"] == "simulation"


def test_missing_backend_fails_without_simulation(monkeypatch):
    monkeypatch.setattr(config, "EMULATION_MODE", False)
    monkeypatch.setattr(orchestrator_bridge, "is_available", lambda: False)
    data = client.post("/api/orchestrator/command", json={"command": "/morning"}).json()
    assert data["success"] is False
    assert data["emulated"] is False
    assert "unavailable" in data["error"]


def test_simulation_is_visible():
    data = client.post("/api/orchestrator/command", json={"command": "/plan"}).json()
    assert data["emulated"] is True
    assert "No vault files were changed" in data["output"]


def test_websocket_rejects_non_object():
    with client.websocket_connect("/api/orchestrator/ws") as websocket:
        websocket.receive_json()
        websocket.send_text("[]")
        assert websocket.receive_json()["type"] == "error"
