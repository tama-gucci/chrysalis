import os
from pathlib import Path
from typing import Optional

class GatewayConfig:
    """Configuration settings for the Ambient Chrysalis Gateway daemon."""

    HOST: str = os.environ.get("CHRYSALIS_GATEWAY_HOST") or os.environ.get("CHRYALIS_GATEWAY_HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("CHRYSALIS_GATEWAY_PORT") or os.environ.get("CHRYALIS_GATEWAY_PORT", "8765"))

    # Optional Bearer Token for securing external access over Cloudflare Tunnel
    AUTH_TOKEN: Optional[str] = os.environ.get("CHRYSALIS_GATEWAY_TOKEN") or os.environ.get("CHRYALIS_GATEWAY_TOKEN", None)

    # Path to Antigravity headless language server CLI
    AGENTAPI_BIN_PATH: str = (
        os.environ.get("CHRYSALIS_AGENTAPI_PATH")
        or os.environ.get("CHRYALIS_AGENTAPI_PATH")
        or os.environ.get("AGENTAPI_BIN_PATH")
        or (
            str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "antigravity" / "resources" / "bin" / "language_server.exe")
            if os.environ.get("LOCALAPPDATA") and (Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "antigravity" / "resources" / "bin" / "language_server.exe").exists()
            else str(Path.home() / ".gemini" / "antigravity" / "bin" / "agentapi")
        )
    )

    # Active workstation node profile name (generic fallback)
    ACTIVE_PROFILE: str = os.environ.get("CHRYSALIS_NODE_PROFILE") or os.environ.get("CHRYALIS_NODE_PROFILE", "station-node")

    # Framework version
    VERSION: str = "1.0.0"

    # Emulation mode fallback when agentapi binary is missing (e.g. testing/CI)
    EMULATION_MODE: bool = (
        os.environ.get("CHRYSALIS_EMULATION_MODE") or os.environ.get("CHRYALIS_EMULATION_MODE", "false")
    ).lower() in ("true", "1", "yes")

config = GatewayConfig()
