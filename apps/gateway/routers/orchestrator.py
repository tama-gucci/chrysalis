import json
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Security,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from config import config
from orchestrator_bridge import orchestrator_bridge

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])
security = HTTPBearer(auto_error=False)


def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> bool:
    if not config.AUTH_TOKEN:
        return True
    if not credentials or credentials.credentials != config.AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True


class CommandRequest(BaseModel):
    command: str = Field(..., description="Slash command (e.g. /morning, /doctor) or prompt")
    args: Optional[Dict[str, Any]] = Field(default=None, description="Command arguments")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Alias for command arguments")
    conversation_id: Optional[str] = Field(default=None, description="Active Antigravity conversation ID")
    model: Optional[str] = Field(default="flash", description="Antigravity CLI model tier (flash_lite, flash, or pro)")


class CommandResponse(BaseModel):
    success: bool
    command: str
    output: str
    error: Optional[str] = None
    conversation_id: Optional[str] = None
    execution_time_ms: int
    timestamp: str
    emulated: Optional[bool] = None


@router.post("/command", response_model=CommandResponse)
async def execute_command(
    request: CommandRequest,
    authorized: bool = Depends(verify_token),
):
    """Executes a Chrysalis slash command or chat turn via Google Antigravity."""
    cmd_args = request.args if request.args is not None else request.parameters
    result = await orchestrator_bridge.execute_command(
        command=request.command,
        args=cmd_args,
        conversation_id=request.conversation_id,
        model=request.model,
    )
    return CommandResponse(**result)


@router.get("/status")
async def get_status(authorized: bool = Depends(verify_token)):
    """Returns the live status, uptime, and availability of the orchestrator gateway."""
    return orchestrator_bridge.get_status()


@router.websocket("/ws")
async def orchestrator_websocket(websocket: WebSocket):
    """Real-time bidirectional WebSocket streaming between Chrysalis Mobile and Antigravity."""
    await websocket.accept()

    # Check token authentication if configured
    if config.AUTH_TOKEN:
        token = websocket.query_params.get("token")
        if not token or token != config.AUTH_TOKEN:
            await websocket.send_json({
                "type": "error",
                "message": "Unauthorized: invalid token",
                "content": "Unauthorized: invalid token",
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    # Emit initial status frame
    status_data = orchestrator_bridge.get_status()
    await websocket.send_json({
        "type": "status",
        "data": status_data,
        "metadata": status_data,
        "content": status_data.get("status", "online"),
    })

    try:
        while True:
            text = await websocket.receive_text()
            try:
                msg = json.loads(text)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "content": "Invalid JSON format",
                })
                continue

            if not isinstance(msg, dict):
                await websocket.send_json({"type": "error", "content": "Expected a JSON object"})
                continue
            msg_type = msg.get("type", "command")

            if msg_type == "ping":
                now_iso = datetime.now().astimezone().isoformat()
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": now_iso,
                    "content": "pong",
                })
            elif msg_type == "status":
                status_payload = orchestrator_bridge.get_status()
                await websocket.send_json({
                    "type": "status",
                    "data": status_payload,
                    "metadata": status_payload,
                    "content": status_payload.get("status", "online"),
                })
            elif msg_type == "command":
                cmd = msg.get("command", "")
                args = msg.get("args") if msg.get("args") is not None else msg.get("parameters")
                conv_id = msg.get("conversation_id")
                model = msg.get("model")

                chunk_text = f"Dispatching command: {cmd}..."
                await websocket.send_json({
                    "type": "chunk",
                    "data": chunk_text,
                    "content": chunk_text,
                })

                result = await orchestrator_bridge.execute_command(
                    command=cmd,
                    args=args,
                    conversation_id=conv_id,
                    model=model,
                )

                await websocket.send_json({
                    "type": "complete" if result.get("success") else "error",
                    "success": result.get("success", False),
                    "data": result,
                    "metadata": result,
                    "content": result.get("output") or result.get("error", ""),
                })
            else:
                err_msg = f"Unsupported message type: {msg_type}"
                await websocket.send_json({
                    "type": "error",
                    "message": err_msg,
                    "content": err_msg,
                })
    except WebSocketDisconnect:
        pass
