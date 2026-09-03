#!/usr/bin/env bash
# Chrysalis Root Bootstrap & Setup Launcher
# Detects environment timezone offset, verifies required directories,
# seeds operational memory and roadmaps from templates if not present.

python3 - <<'EOF'
import os
import sys
import datetime
from pathlib import Path

VAULT_ROOT = Path(".").resolve()

def get_local_timezone_offset():
    """Detect local timezone offset in format '+HH:MM' or '-HH:MM'."""
    now = datetime.datetime.now().astimezone()
    offset = now.strftime("%z")
    if len(offset) == 5:
        return f"{offset[:3]}:{offset[3:]}"
    return "-05:00"

def get_iso_timestamp(offset):
    """Generate ISO timestamp with explicit local timezone."""
    now = datetime.datetime.now()
    return f"{now.strftime('%Y-%m-%dT%H:%M:%S')}{offset}"

def ensure_directories():
    """Ensure standard Chrysalis folder substrate exists."""
    dirs = [
        VAULT_ROOT / "TaskNotes" / "Tasks",
        VAULT_ROOT / "TaskNotes" / "Archive",
        VAULT_ROOT / "TaskNotes" / "Views",
        VAULT_ROOT / "TaskNotes" / "Workflows",
        VAULT_ROOT / "TaskNotes" / "_templates",
        VAULT_ROOT / "Slipbox",
        VAULT_ROOT / "Projects" / "_templates",
        VAULT_ROOT / "System" / "_templates",
        VAULT_ROOT / "System" / "Orchestrators",
        VAULT_ROOT / ".agent" / "skills",
        VAULT_ROOT / "_types"
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print("  ✓ Directory substrate verified.")

def seed_system_memory(offset, timestamp):
    """Seed System/Scheduling-Memory.md from template if missing."""
    mem_path = VAULT_ROOT / "System" / "Scheduling-Memory.md"
    template_path = VAULT_ROOT / "System" / "_templates" / "Scheduling-Memory.template.md"
    
    if not mem_path.exists():
        if template_path.exists():
            content = template_path.read_text(encoding="utf-8")
            content = content.replace("{{TIMEZONE_OFFSET}}", offset)
            content = content.replace("{{TIMESTAMP}}", timestamp)
            mem_path.write_text(content, encoding="utf-8")
            print("  ✓ Created System/Scheduling-Memory.md from template.")
        else:
            print("  ! Template not found, skipping Scheduling-Memory creation.")
    else:
        print("  ✓ System/Scheduling-Memory.md already exists.")

def seed_life_roadmap(offset, timestamp):
    """Seed System/Life-Roadmap.md from template if missing."""
    roadmap_path = VAULT_ROOT / "System" / "Life-Roadmap.md"
    template_path = VAULT_ROOT / "System" / "_templates" / "Life-Roadmap.template.md"
    
    if not roadmap_path.exists():
        if template_path.exists():
            today = datetime.date.today()
            d_end = today + datetime.timedelta(days=14)
            d_m2_start = d_end + datetime.timedelta(days=1)
            d_m2_end = d_m2_start + datetime.timedelta(days=28)
            
            content = template_path.read_text(encoding="utf-8")
            content = content.replace("{{TIMESTAMP}}", timestamp)
            content = content.replace("{{DATE_START}}", today.strftime("%Y-%m-%d"))
            content = content.replace("{{DATE_END}}", d_end.strftime("%Y-%m-%d"))
            content = content.replace("{{DATE_M2_START}}", d_m2_start.strftime("%Y-%m-%d"))
            content = content.replace("{{DATE_M2_END}}", d_m2_end.strftime("%Y-%m-%d"))
            roadmap_path.write_text(content, encoding="utf-8")
            print("  ✓ Created System/Life-Roadmap.md from template.")
        else:
            print("  ! Template not found, skipping Life-Roadmap creation.")
    else:
        print("  ✓ System/Life-Roadmap.md already exists.")

def main():
    print("=======================================================")
    print("    Chrysalis - Autonomous Bootstrap & Setup Engine    ")
    print("=======================================================")
    
    offset = get_local_timezone_offset()
    timestamp = get_iso_timestamp(offset)
    print(f"  Detected Local Timezone Offset: {offset}")
    print(f"  Vault Substrate Path:          {VAULT_ROOT}")
    print()

    print("[1/3] Verifying Substrate...")
    ensure_directories()
    
    print("\n[2/3] Seeding Operational Memory & Roadmaps...")
    seed_system_memory(offset, timestamp)
    seed_life_roadmap(offset, timestamp)
    
    print("\n[3/3] Orchestrator & Obsidian Instructions:")
    print("  -----------------------------------------------------")
    print("  1. Obsidian Setup:")
    print("     • Open Obsidian -> 'Open folder as vault' -> select this directory.")
    print("     • Click 'Enable community plugins' when prompted.")
    print("  2. Conversational Onboarding:")
    print("     • In your AI agent chat, run:")
    print("       /onboard")
    print("     • Answer 4 quick questions to customize your pillars and goals.")
    print("  3. Daily Production Operation:")
    print("     • Morning (08:30): /morning")
    print("     • Evening (21:00): /evening")
    print("     • Health Check:   /doctor")
    print("=======================================================\n")

if __name__ == "__main__":
    main()
EOF

