import asyncio
import json
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from config import config

def _format_local_iso_timestamp() -> str:
    """Formats current wall-clock time with explicit local timezone offset (e.g. -05:00)."""
    return datetime.now().astimezone().isoformat(timespec="seconds")

class BaseOrchestratorBridge(ABC):
    """Abstract base contract for pluggable autonomous agent orchestrators."""

    @abstractmethod
    def is_available(self) -> bool:
        """Verifies whether the agent orchestrator is installed and executable."""
        pass

    @abstractmethod
    async def execute_command(
        self,
        command: str,
        args: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes a Chrysalis slash command or conversational turn."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Returns real-time orchestrator health, engine telemetry, and uptime."""
        pass


class AntigravityBridge(BaseOrchestratorBridge):
    """Reference implementation bridging to Google Antigravity language_server / agentapi."""

    def __init__(self, agentapi_bin_path: Optional[str] = None):
        self.agentapi_path = agentapi_bin_path or config.AGENTAPI_BIN_PATH
        self._start_time = time.time()

    def is_available(self) -> bool:
        """Verifies whether the agentapi executable exists and has execute permissions."""
        import sys
        path = Path(self.agentapi_path)
        if sys.platform == "win32":
            if path.is_file():
                return True
            for ext in (".exe", ".bat", ".cmd"):
                if path.with_suffix(ext).is_file():
                    return True
            return False
        return path.is_file() and os.access(path, os.X_OK)

    async def execute_command(
        self,
        command: str,
        args: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes a Chrysalis slash command or natural language prompt via agentapi."""
        start_time = time.perf_counter()

        # Format command prompt with arguments if provided
        prompt = command.strip()
        if args:
            args_str = " ".join(f"--{k}={v}" for k, v in args.items())
            prompt = f"{prompt} {args_str}".strip()

        if not prompt:
            return self._failure(command, "Command must not be empty", conversation_id)
        if not self.is_available() and not config.EMULATION_MODE:
            return self._failure(command, "Antigravity is unavailable. Configure CHRYSALIS_AGENTAPI_PATH; no action was executed.", conversation_id)

        # Real execution is distinct from explicitly enabled test emulation.
        if self.is_available() and not config.EMULATION_MODE:
            try:
                if self.agentapi_path.lower().endswith(".bat") or self.agentapi_path.lower().endswith(".cmd"):
                    cmd_args = ["cmd.exe", "/c", self.agentapi_path]
                elif self.agentapi_path.lower().endswith("language_server.exe"):
                    cmd_args = [self.agentapi_path, "agentapi"]
                else:
                    cmd_args = [self.agentapi_path]
                if conversation_id:
                    cmd_args.extend(["send-message", conversation_id, prompt])
                else:
                    cmd_args.append("new-conversation")
                    if model in ("flash_lite", "flash", "pro"):
                        cmd_args.append(f"--model={model}")
                    cmd_args.append(prompt)

                process = await asyncio.create_subprocess_exec(
                    *cmd_args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                try:
                    stdout_b, stderr_b = await asyncio.wait_for(process.communicate(), timeout=60.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    process.kill()
                    await process.communicate()
                    raise
                stdout = stdout_b.decode("utf-8", errors="replace").strip()
                stderr = stderr_b.decode("utf-8", errors="replace").strip()

                elapsed_ms = int((time.perf_counter() - start_time) * 1000)

                if process.returncode == 0:
                    conv_id = conversation_id
                    if not conv_id and stdout:
                        try:
                            parsed = json.loads(stdout)
                            conv_id = (
                                parsed.get("response", {})
                                .get("newConversation", {})
                                .get("conversationId")
                            )
                        except Exception:
                            pass
                    return {
                        "success": True,
                        "command": command,
                        "output": stdout if stdout else "Command executed successfully.",
                        "conversation_id": conv_id or "auto-created",
                        "execution_time_ms": elapsed_ms,
                        "timestamp": _format_local_iso_timestamp(),
                    }
                else:
                    return {
                        "success": False,
                        "command": command,
                        "output": stdout,
                        "error": stderr or f"Process exited with code {process.returncode}",
                        "conversation_id": conversation_id,
                        "execution_time_ms": elapsed_ms,
                        "timestamp": _format_local_iso_timestamp(),
                    }
            except asyncio.TimeoutError:
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                return {
                    "success": False,
                    "command": command,
                    "output": "",
                    "error": "Execution timed out after 60 seconds",
                    "conversation_id": conversation_id,
                    "execution_time_ms": elapsed_ms,
                    "timestamp": _format_local_iso_timestamp(),
                }
            except Exception as e:
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                return {
                    "success": False,
                    "command": command,
                    "output": "",
                    "error": str(e),
                    "conversation_id": conversation_id,
                    "execution_time_ms": elapsed_ms,
                    "timestamp": _format_local_iso_timestamp(),
                }

        # Emulation mode fallback (CI/testing/remote development environments)
        await asyncio.sleep(0.05)  # Simulate brief processing latency
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        output = self._emulate_command_output(command, args)

        return {
            "success": True,
            "command": command,
            "output": output,
            "conversation_id": conversation_id or "simulated-conv-001",
            "execution_time_ms": elapsed_ms,
            "timestamp": _format_local_iso_timestamp(),
            "emulated": True,
        }

    @staticmethod
    def _failure(command, error, conversation_id=None):
        return {"success": False, "command": command, "output": "", "error": error,
                "conversation_id": conversation_id, "execution_time_ms": 0,
                "timestamp": _format_local_iso_timestamp(), "emulated": False}

    def _emulate_command_output(self, command, args):
        return f"[SIMULATION ONLY] Received {command}. No vault files were changed."

    def get_status(self) -> Dict[str, Any]:
        """Returns real-time orchestrator health and telemetry."""
        return {
            "status": "simulation" if config.EMULATION_MODE else ("online" if self.is_available() else "unavailable"),
            "adapter": "antigravity",
            "agentapi_available": self.is_available(),
            "agentapi_path": self.agentapi_path,
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "active_profile": config.ACTIVE_PROFILE,
            "version": config.VERSION,
            "emulation_mode": config.EMULATION_MODE,
            "timestamp": _format_local_iso_timestamp(),
        }


class UnimplementedBridge(BaseOrchestratorBridge):
    """Reserved adapter; never reports successful execution."""
    adapter = "unimplemented"

    def __init__(self, endpoint_url=None):
        self.endpoint_url = endpoint_url

    def is_available(self):
        return False

    async def execute_command(self, command, args=None, conversation_id=None, model=None):
        return AntigravityBridge._failure(command, f"{self.adapter} adapter is not implemented", conversation_id)

    def get_status(self):
        return {"status": "unavailable", "adapter": self.adapter,
                "timestamp": _format_local_iso_timestamp()}


class OpenClawBridge(UnimplementedBridge):
    adapter = "openclaw"


class HermesOSBridge(UnimplementedBridge):
    adapter = "hermes_os"


# Backward-compatible alias
OrchestratorBridge = AntigravityBridge

# Active bridge instance
orchestrator_bridge: BaseOrchestratorBridge = AntigravityBridge()
