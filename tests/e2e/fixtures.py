"""
Shared fixtures, sandbox environments, and verification helpers for Chrysalis E2E tests.
Enforces opaque-box testing, zero personal data usage, and complete sandbox isolation.
"""

import os
import re
import sys
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Known PII patterns that must NEVER exist in public framework files or test fixtures
PII_PATTERNS = [
    (re.compile(r"/home/(?!user|runner|sandbox)[a-zA-Z0-9_\-]+/"), "Machine path (/home/<user>/)"),
    (re.compile(r"[a-zA-Z]:\\[Uu]sers\\(?!user|runner|sandbox)[a-zA-Z0-9_\-]+"), "Windows user path"),
    (re.compile(r"[a-zA-Z0-9_\.\-]+@group\.calendar\.google\.com"), "Google Calendar ID"),
    (re.compile(r"AIzaSy[a-zA-Z0-9_\-]{33}"), "Google API Key"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub Personal Access Token"),
]

TIMEZONE_OFFSET_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[+\-][0-9]{2}:[0-9]{2}$")
RAW_UTC_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """
    Parses YAML frontmatter and markdown body from markdown string.
    Returns (frontmatter_dict, body_content).
    """
    if not content.startswith("---"):
        return {}, content
    
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    
    fm_raw = parts[1]
    body = parts[2]
    try:
        data = yaml.safe_load(fm_raw)
        return data if isinstance(data, dict) else {}, body
    except Exception as e:
        raise ValueError(f"YAML frontmatter parsing failed: {e}") from e


def read_frontmatter(file_path: Path) -> Tuple[Dict[str, Any], str]:
    """Reads a file and returns its parsed frontmatter and body."""
    if not file_path.exists():
        raise FileNotFoundError(f"File does not exist: {file_path}")
    text = file_path.read_text(encoding="utf-8")
    return parse_frontmatter(text)


def scan_for_pii(text: str) -> List[Tuple[str, str]]:
    """
    Scans a text string for sensitive PII or machine path patterns.
    Returns list of (matched_substring, pattern_description).
    """
    violations = []
    for pattern, desc in PII_PATTERNS:
        matches = pattern.findall(text)
        for m in matches:
            violations.append((m, desc))
    return violations


def run_cmd(args: List[str], cwd: Optional[Path] = None, env: Optional[Dict[str, str]] = None, timeout: int = 90) -> Tuple[int, str, str]:
    """
    Executes a command and returns (returncode, stdout, stderr).
    """
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    
    cmd_args = list(args)
    if cmd_args:
        if cmd_args[0] in ("python", "python3"):
            cmd_args[0] = sys.executable
        elif cmd_args[0] in ("bash", "sh"):
            if sys.platform == "win32":
                git_usr_bin = Path(r"C:\tools\git\usr\bin")
                if git_usr_bin.exists():
                    current_path = run_env.get("PATH", "")
                    if str(git_usr_bin) not in current_path:
                        run_env["PATH"] = f"{git_usr_bin};{current_path}"
                sh_exe = (
                    shutil.which("bash", path=run_env.get("PATH"))
                    or shutil.which("sh", path=run_env.get("PATH"))
                    or (str(git_usr_bin / "sh.exe") if git_usr_bin.exists() else cmd_args[0])
                )
                cmd_args[0] = sh_exe
    
    run_env["PYTHONIOENCODING"] = "utf-8"
    run_env["PYTHONUTF8"] = "1"
    run_env["CHRYSALIS_OFFLINE_SYNC"] = "1"
    proc = subprocess.run(
        cmd_args,
        cwd=str(cwd or REPO_ROOT),
        env=run_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout
    )
    return proc.returncode, proc.stdout, proc.stderr


class SandboxVault:
    """
    Creates an isolated temporary mock Chrysalis vault for non-destructive testing.
    Can be configured to simulate either:
    1. A fresh uninitialized vault.
    2. An active personal runtime vault holding simulated private tasks, daily notes,
       live memory, and workstation manifests (all using synthetic data).
    """
    def __init__(self, populate_runtime: bool = False, prefix: str = "chrysalis_test_vault_"):
        self.tmp_dir = tempfile.TemporaryDirectory(prefix=prefix)
        self.path = Path(self.tmp_dir.name).resolve()
        if populate_runtime:
            self._populate_mock_runtime()

    def _populate_mock_runtime(self):
        """Populates synthetic runtime files mirroring live personal installation."""
        # Folders
        (self.path / "TaskNotes" / "Tasks").mkdir(parents=True, exist_ok=True)
        (self.path / "TaskNotes" / "Archive").mkdir(parents=True, exist_ok=True)
        (self.path / "Projects" / "Synthetic_Project").mkdir(parents=True, exist_ok=True)
        (self.path / "Slipbox").mkdir(parents=True, exist_ok=True)
        (self.path / "System" / "Environment").mkdir(parents=True, exist_ok=True)
        (self.path / ".obsidian" / "plugins" / "tasknotes").mkdir(parents=True, exist_ok=True)
        (self.path / ".agent" / "skills" / ".backup").mkdir(parents=True, exist_ok=True)

        # 1. Private Active Task
        task_content = """---
title: "Synthetic Private Task For Testing"
status: todo
dateCreated: "2026-09-03T10:00:00-05:00"
due: "2026-09-05"
scheduled: "2026-09-03T11:00:00-05:00"
priority: high
urgency_tier: 3
modality: analytical
timeEstimate: 45
energy: high
friction: low
micro_chunked: false
tags:
  - task
  - pillar-core/research
googleCalendarEventId: "synth_cal_event_123"
---
# Synthetic Private Task Notes
Do not overwrite or wipe during framework synchronization!
"""
        (self.path / "TaskNotes" / "Tasks" / "20260903-synthetic-task.md").write_text(task_content, encoding="utf-8")

        # 2. Private Archived Task
        archive_content = """---
title: "Historical Completed Task"
status: archived
dateCreated: "2026-09-01T08:00:00-05:00"
due: "2026-09-01"
scheduled: null
priority: normal
urgency_tier: 1
modality: administrative
timeEstimate: 15
energy: low
friction: low
micro_chunked: false
tags:
  - task
  - pillar-ops/admin
---
Completed task note.
"""
        (self.path / "TaskNotes" / "Archive" / "20260901-completed-task.md").write_text(archive_content, encoding="utf-8")

        # 3. Daily Note
        daily_content = """---
date: 2026-09-03
wake: "08:30:00-05:00"
energy: 4
---
# Daily Focus Log - 2026-09-03
Personal daily reflections and timeblocks.
"""
        (self.path / "2026-09-03.md").write_text(daily_content, encoding="utf-8")

        # 4. Live Memory State
        memory_content = """---
active_timezone: "-05:00"
rolling_avg_wake_weekday: "08:45"
diurnal_offsets:
  peak_focus_start: "10:30"
  slump_start: "14:00"
dynamic_multipliers:
  analytical: 1.15
  kinetic: 0.90
  synthesis: 1.05
  administrative: 1.00
pause_state:
  is_paused: false
  mode: null
candidate_task_pools:
  quick_wins: []
---
# Live Operational Scheduling Memory
"""
        (self.path / "System" / "Scheduling-Memory.md").write_text(memory_content, encoding="utf-8")

        # 5. Live Roadmap
        roadmap_content = """---
version: 5.0.0
last_updated: "2026-09-03T10:00:00-05:00"
pillars:
  - id: pillar-core
    title: Core Research
    tags: [pillar-core/research]
  - id: pillar-ops
    title: Operations
    tags: [pillar-ops/admin]
---
# Life Strategic Roadmap
"""
        (self.path / "System" / "Life-Roadmap.md").write_text(roadmap_content, encoding="utf-8")

        # 6. Workstation Manifest
        manifest_content = """---
system_name: "test-node"
role: "workstation"
---
# System Manifest: test-node
"""
        (self.path / "System" / "Environment" / "test-node.md").write_text(manifest_content, encoding="utf-8")

        # 7. Obsidian plugin config with personal calendar settings
        data_json_content = """{
  "targetCalendarId": "synthetic-user-cal@example.com",
  "googleCalendarDeletionQueue": [],
  "googleCalendarEventIndex": []
}"""
        (self.path / ".obsidian" / "plugins" / "tasknotes" / "data.json").write_text(data_json_content, encoding="utf-8")

    def cleanup(self):
        """Clean up the temporary directory."""
        self.tmp_dir.cleanup()

    def count_files(self) -> int:
        """Returns total file count in sandbox."""
        count = 0
        for _, _, files in os.walk(self.path):
            count += len(files)
        return count
