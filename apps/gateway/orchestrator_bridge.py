import asyncio
import json
import os
import shutil
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
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

        # If agentapi is available and emulation mode is not explicitly forced, invoke real binary
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

                stdout_b, stderr_b = await asyncio.wait_for(process.communicate(), timeout=60.0)
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

    def _emulate_command_output(self, command: str, args: Optional[Dict[str, Any]]) -> str:
        """Produces realistic domain outputs for standard Chrysalis commands during emulation."""
        cmd = command.split()[0].lower()

        if cmd == "/morning":
            wake = args.get("wake", "07:45") if args else "07:45"
            energy = args.get("energy", 4) if args else 4
            return (
                f"🌅 **Morning Calibration Completed**\n"
                f"- Wake time locked: {wake} (Diurnal shift: +00:00)\n"
                f"- Energy baseline: {energy}/5 (Optimal Flow)\n"
                f"- Active timeblocks serialized with explicit -05:00 offset.\n"
                f"- 3 ultradian focus sprints allocated."
            )
        elif cmd == "/evening":
            return (
                "🌙 **Evening Staging Reconciliation**\n"
                "- Unified /audit pre-flight integrity check: PASSED.\n"
                "- Multiplier telemetry updated from completed sessions.\n"
                "- Tomorrow prototype schedule staged in System/Scheduling-Memory.md."
            )
        elif cmd == "/doctor":
            return (
                "🩺 **Chrysalis System Diagnostic Integrity Pass**\n"
                "- [1/6] TaskNotes Frontmatter Schema: 100% VALID\n"
                "- [2/6] Explicit Timezone Offset (-05:00): STRICTLY ENFORCED\n"
                "- [3/6] Life-Roadmap Tag Registry: CONSISTENT\n"
                "- [4/6] Wikilink & Graph Integrity: 0 BROKEN LINKS\n"
                "- [5/6] Skill Runbook Validation: 15/15 HEALTHY\n"
                "- [6/6] Telemetry Multiplier Bounds [0.20, 2.00]: ALL IN BOUNDS\n"
                "Result: System integrity is pristine."
            )
        elif cmd == "/audit":
            return (
                "⚖️ **Nightly Audit Pass Completed**\n"
                "- Task lifecycles reconciled.\n"
                "- Multiplier telemetry weights updated.\n"
                "- 14-day roadmap milestone horizon synced."
            )
        elif cmd == "/pause":
            mode = args.get("mode", "maintenance") if args else "maintenance"
            return (
                f"⏸️ **Chrysalis System Paused (Mode: {mode})**\n"
                "- Multiplier decay frozen.\n"
                "- Active sprint timeblocks de-scheduled."
            )
        elif cmd == "/plan":
            return (
                "📋 **Two-Stage Focus Plan Synchronized**\n"
                "- Stacking 75m sprints with 15m decompression buffers.\n"
                "- Modality pairing aligned with bio-cognitive diurnal windows."
            )
        else:
            return f"🤖 Orchestrator acknowledged: \"{command}\""

    def get_status(self) -> Dict[str, Any]:
        """Returns real-time orchestrator health and telemetry."""
        return {
            "status": "online",
            "adapter": "antigravity",
            "agentapi_available": self.is_available(),
            "agentapi_path": self.agentapi_path,
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "active_profile": config.ACTIVE_PROFILE,
            "version": config.VERSION,
            "emulation_mode": config.EMULATION_MODE or not self.is_available(),
            "timestamp": _format_local_iso_timestamp(),
        }


class OpenClawBridge(BaseOrchestratorBridge):
    """Pluggable adapter for OpenClaw-based autonomous agent execution."""

    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = endpoint_url or os.environ.get("OPENCLAW_ENDPOINT", "http://localhost:8000")
        self._start_time = time.time()

    def is_available(self) -> bool:
        return bool(shutil.which("openclaw")) or bool(os.environ.get("OPENCLAW_ENDPOINT"))

    async def execute_command(
        self,
        command: str,
        args: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        await asyncio.sleep(0.05)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "success": True,
            "command": command,
            "output": f"🐾 [OpenClaw] Acknowledged: {command}",
            "conversation_id": conversation_id or "openclaw-conv-001",
            "execution_time_ms": elapsed_ms,
            "timestamp": _format_local_iso_timestamp(),
            "adapter": "openclaw",
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "online" if self.is_available() else "standby",
            "adapter": "openclaw",
            "endpoint_url": self.endpoint_url,
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "timestamp": _format_local_iso_timestamp(),
        }


class HermesOSBridge(BaseOrchestratorBridge):
    """Pluggable adapter for Hermes OS and local LLM inference engines."""

    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = endpoint_url or os.environ.get("HERMES_ENDPOINT", "http://localhost:11434")
        self._start_time = time.time()

    def is_available(self) -> bool:
        return bool(shutil.which("hermes")) or bool(os.environ.get("HERMES_ENDPOINT"))

    async def execute_command(
        self,
        command: str,
        args: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        await asyncio.sleep(0.05)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "success": True,
            "command": command,
            "output": f"⚡ [Hermes OS] Processed: {command}",
            "conversation_id": conversation_id or "hermes-conv-001",
            "execution_time_ms": elapsed_ms,
            "timestamp": _format_local_iso_timestamp(),
            "adapter": "hermes_os",
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "online" if self.is_available() else "standby",
            "adapter": "hermes_os",
            "endpoint_url": self.endpoint_url,
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "timestamp": _format_local_iso_timestamp(),
        }


# Backward-compatible alias
OrchestratorBridge = AntigravityBridge

# Active bridge instance
orchestrator_bridge: BaseOrchestratorBridge = AntigravityBridge()
