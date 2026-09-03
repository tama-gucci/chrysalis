#!/usr/bin/env bash
# ==============================================================================
# Chrysalis Framework: Upstream-to-Runtime Synchronization Engine
# Propagates framework updates from chrysalis-git into the active chrysalis vault
# while strictly safeguarding all personal notes, tasks, roadmaps, and telemetry.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GIT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET_RUNTIME="/home/sin/GoogleDrive/chrysalis"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}   🦋  Chrysalis Framework: Upstream Update Sync       ${NC}"
echo -e "${BLUE}=======================================================${NC}"

if [ ! -d "$TARGET_RUNTIME" ]; then
    echo -e "${RED}❌ Target runtime vault not found at $TARGET_RUNTIME${NC}"
    exit 1
fi

echo -e "${GREEN}Source (Upstream):${NC} $GIT_ROOT"
echo -e "${GREEN}Target (Runtime): ${NC} $TARGET_RUNTIME"
echo ""

# 1. Root Framework Files
echo -e "${BLUE}[1/8] Updating Root Framework Files...${NC}"
cp -v "$GIT_ROOT/AGENTS.md" "$TARGET_RUNTIME/AGENTS.md"
cp -v "$GIT_ROOT/README.md" "$TARGET_RUNTIME/README.md"
cp -v "$GIT_ROOT/LICENSE" "$TARGET_RUNTIME/LICENSE"
cp -v "$GIT_ROOT/bootstrap.sh" "$TARGET_RUNTIME/bootstrap.sh"
cp -v "$GIT_ROOT/Dashboard.md" "$TARGET_RUNTIME/Dashboard.md"
cp -v "$GIT_ROOT/mdbase.yaml" "$TARGET_RUNTIME/mdbase.yaml"

# 2. Type definitions
echo -e "${BLUE}[2/8] Updating Type Definitions...${NC}"
mkdir -p "$TARGET_RUNTIME/_types"
cp -vr "$GIT_ROOT/_types/"* "$TARGET_RUNTIME/_types/"

# 3. Agent Skills (Runtime only, preserving local skills.json)
echo -e "${BLUE}[3/8] Updating Runtime Agent Skills...${NC}"
mkdir -p "$TARGET_RUNTIME/.agent/skills"
for skill_dir in "$GIT_ROOT/.agent/skills"/*; do
    if [ -d "$skill_dir" ] && [ "$(basename "$skill_dir")" != ".backup" ]; then
        skill_name="$(basename "$skill_dir")"
        mkdir -p "$TARGET_RUNTIME/.agent/skills/$skill_name"
        cp -vr "$skill_dir/"* "$TARGET_RUNTIME/.agent/skills/$skill_name/"
    fi
done

# 4. System Specs & Environment Utilities
echo -e "${BLUE}[4/8] Updating System Specifications & Environment Tools...${NC}"
mkdir -p "$TARGET_RUNTIME/System/Orchestrators"
mkdir -p "$TARGET_RUNTIME/System/Environment/scripts"
mkdir -p "$TARGET_RUNTIME/System/Environment/_templates"
mkdir -p "$TARGET_RUNTIME/System/_templates"

cp -v "$GIT_ROOT/System/Runtime-Constitution.md" "$TARGET_RUNTIME/System/Runtime-Constitution.md"
cp -v "$GIT_ROOT/System/SYSTEM-PROMPT.md" "$TARGET_RUNTIME/System/SYSTEM-PROMPT.md"
cp -vr "$GIT_ROOT/System/Orchestrators/"* "$TARGET_RUNTIME/System/Orchestrators/"
cp -v "$GIT_ROOT/System/Environment/Environment-Index.md" "$TARGET_RUNTIME/System/Environment/Environment-Index.md"
cp -vr "$GIT_ROOT/System/Environment/scripts/"* "$TARGET_RUNTIME/System/Environment/scripts/"

# 5. Templates (System, Projects, TaskNotes, Environment)
echo -e "${BLUE}[5/8] Updating Templates Matrix...${NC}"
cp -vr "$GIT_ROOT/System/_templates/"* "$TARGET_RUNTIME/System/_templates/"
cp -vr "$GIT_ROOT/System/Environment/_templates/"* "$TARGET_RUNTIME/System/Environment/_templates/"

mkdir -p "$TARGET_RUNTIME/Projects/_templates"
cp -vr "$GIT_ROOT/Projects/_templates/"* "$TARGET_RUNTIME/Projects/_templates/"

mkdir -p "$TARGET_RUNTIME/TaskNotes/_templates"
cp -vr "$GIT_ROOT/TaskNotes/_templates/"* "$TARGET_RUNTIME/TaskNotes/_templates/"

# 6. Projects & Slipbox Readmes
echo -e "${BLUE}[6/8] Updating Documentation Readmes...${NC}"
cp -v "$GIT_ROOT/Projects/README.md" "$TARGET_RUNTIME/Projects/README.md"
cp -v "$GIT_ROOT/Slipbox/README.md" "$TARGET_RUNTIME/Slipbox/README.md"

# 7. TaskNotes Views & Workflows
echo -e "${BLUE}[7/8] Updating TaskNotes Views & Workflows...${NC}"
mkdir -p "$TARGET_RUNTIME/TaskNotes/Views"
mkdir -p "$TARGET_RUNTIME/TaskNotes/Workflows"
mkdir -p "$TARGET_RUNTIME/TaskNotes/Tasks"

cp -vr "$GIT_ROOT/TaskNotes/Views/"* "$TARGET_RUNTIME/TaskNotes/Views/"
cp -vr "$GIT_ROOT/TaskNotes/Workflows/"* "$TARGET_RUNTIME/TaskNotes/Workflows/"
cp -v "$GIT_ROOT/TaskNotes/Tasks/example-task.md" "$TARGET_RUNTIME/TaskNotes/Tasks/example-task.md"

# 8. Clean Obsidian Plugins
echo -e "${BLUE}[8/8] Updating Obsidian Plugins (Code & Manifests)...${NC}"
mkdir -p "$TARGET_RUNTIME/.obsidian/plugins"
for plugin_dir in "$GIT_ROOT/.obsidian/plugins"/*; do
    if [ -d "$plugin_dir" ]; then
        p_name="$(basename "$plugin_dir")"
        mkdir -p "$TARGET_RUNTIME/.obsidian/plugins/$p_name"
        for item in "$plugin_dir"/*; do
            base_item="$(basename "$item")"
            # Do not overwrite data.json or personal databases if they exist in runtime
            if [ "$base_item" != "data.json" ] && [ "$base_item" != "runs" ] && [ "$base_item" != "data" ]; then
                cp -vr "$item" "$TARGET_RUNTIME/.obsidian/plugins/$p_name/"
            fi
        done
    fi
done

echo ""
echo -e "${GREEN}=======================================================${NC}"
echo -e "${GREEN}✅ SYNCHRONIZATION COMPLETE: Runtime vault is up-to-date!${NC}"
echo -e "${GREEN}   Personal tasks, roadmaps, and telemetry untouched.  ${NC}"
echo -e "${GREEN}=======================================================${NC}"
