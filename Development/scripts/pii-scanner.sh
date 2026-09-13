#!/usr/bin/env bash
# ==============================================================================
# Chrysalis Zero-Leak PII & Git Boundary Scanner
# Enforces the Development Constitution against git-tracked files and staging.
# ==============================================================================

set -euo pipefail

# Ensure standard Unix utilities in /usr/bin or git bin are in PATH on Windows MSYS
if [ -d "/usr/bin" ] && [[ ":$PATH:" != *":/usr/bin:"* ]]; then
    export PATH="/usr/bin:$PATH"
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}   🛡️  Chrysalis Development Zero-Leak PII Scanner     ${NC}"
echo -e "${BLUE}=======================================================${NC}"

# Navigate to repo root if not already there
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$REPO_ROOT"

# ------------------------------------------------------------------------------
# 1. Quarantined Path Invariant Check (git ls-files)
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[1/4] Checking git-tracked files against Quarantined Substrates...${NC}"

TRACKED_FILES=$(git ls-files)

while IFS= read -r FILE; do
    [ -z "$FILE" ] && continue

    # Check live personal tasks
    if [[ "$FILE" =~ (^|/)(TaskNotes/Tasks/|chrysalis/Tasks/) ]] && [ "$FILE" != "TaskNotes/Tasks/example-task.md" ] && [ "$FILE" != "chrysalis/Tasks/example-task.md" ]; then
        echo -e "${RED}  ❌ [LEAK] Personal task tracked in git: $FILE${NC}"
        ERRORS=$((ERRORS + 1))
    fi

    # Check task archive
    if [[ "$FILE" =~ (^|/)(TaskNotes/Archive/|chrysalis/Archive/) ]]; then
        echo -e "${RED}  ❌ [LEAK] Task archive tracked in git: $FILE${NC}"
        ERRORS=$((ERRORS + 1))
    fi

    # Check live personal system state
    if [[ "$FILE" =~ (^|/)(System|chrysalis/System)/(Life-Roadmap\.md|Scheduling-Memory\.md|System-Health\.md|Changelog\.md)$ ]]; then
        echo -e "${RED}  ❌ [LEAK] Live personal system state file tracked in git: $FILE${NC}"
        ERRORS=$((ERRORS + 1))
    fi

    # Check daily focus notes
    if [[ "$FILE" =~ (^|/)(chrysalis/Daily/)?[0-9]{4}-[0-9]{2}-[0-9]{2}.*\.md$ ]]; then
        echo -e "${RED}  ❌ [LEAK] Daily personal log note tracked in git: $FILE${NC}"
        ERRORS=$((ERRORS + 1))
    fi

    # Check personal projects
    if [[ "$FILE" =~ (^|/)(Projects|chrysalis/Projects)/ ]] && [[ ! "$FILE" =~ /_templates/ ]] && [ "$FILE" != "Projects/README.md" ] && [ "$FILE" != "chrysalis/Projects/README.md" ]; then
        echo -e "${RED}  ❌ [LEAK] Personal project directory tracked in git: $FILE${NC}"
        ERRORS=$((ERRORS + 1))
    fi

    # Check personal slipbox notes (allow README and templates)
    if [[ "$FILE" =~ (^|/)(Slipbox|chrysalis/Slipbox)/ ]] && [[ ! "$FILE" =~ /_templates/ ]] && [ "$FILE" != "Slipbox/README.md" ] && [ "$FILE" != "chrysalis/Slipbox/README.md" ]; then
        echo -e "${RED}  ❌ [LEAK] Personal slipbox note tracked in git: $FILE${NC}"
        ERRORS=$((ERRORS + 1))
    fi

    # Check personal workstation manifests in System/Environment/
    if [[ "$FILE" =~ ^System/Environment/ ]] && [[ ! "$FILE" =~ ^System/Environment/_templates/ ]] && [[ ! "$FILE" =~ ^System/Environment/scripts/ ]] && [ "$FILE" != "System/Environment/Environment-Index.md" ]; then
        echo -e "${RED}  ❌ [LEAK] Personal workstation manifest tracked in git: $FILE${NC}"
        ERRORS=$((ERRORS + 1))
    fi

    # Check untracked database/cache directories
    if [[ "$FILE" =~ ^(Nexus/|\.conversations/|\.workspaces/|\.obsidian/workspace.*\.json|\.obsidian/plugins/obsidian-git/obsidian_askpass\.sh) ]]; then
        echo -e "${RED}  ❌ [LEAK] Ephemeral cache or workspace database tracked in git: $FILE${NC}"
        ERRORS=$((ERRORS + 1))
    fi

    # Plugin settings are private even when their current values look sanitized.
    if [[ "$FILE" =~ ^\.obsidian/plugins/.*/data\.json$ ]]; then
        echo -e "${RED}  ❌ [LEAK] Plugin settings tracked in git: $FILE${NC}"
        ERRORS=$((ERRORS + 1))
    fi

    # Check secrets, credentials, tokens
    if [[ "$FILE" =~ \.token\.json$ ]] || [[ "$FILE" =~ credentials.*\.json$ ]] || [[ "$FILE" =~ \.env$ ]] || [[ "$FILE" =~ \.sqlite[0-9]?$ ]] || [[ "$FILE" =~ \.db$ ]]; then
        echo -e "${RED}  ❌ [LEAK] Secret or database file tracked in git: $FILE${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done <<< "$TRACKED_FILES"

if [ "$ERRORS" -eq 0 ]; then
    echo -e "${GREEN}  ✓ No quarantined personal files are tracked in git.${NC}"
fi

# ------------------------------------------------------------------------------
# 2. Deep Content Regex Scanner for Machine Paths & PII
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[2/4] Scanning tracked text files for personal paths and PII...${NC}"

CONTENT_LEAKS=0
PATH_EXCLUDES=(':!*.js' ':!*.wasm' ':!*.css' ':!*.png' ':!*.jpg' ':!*.jpeg' ':!*.gif' ':!*.ico' ':!*.sqlite' ':!*.sqlite3' ':!*.db')

# Check for hardcoded /home/ or /Users/ paths
MATCHES=$(git grep -nE '(/home/[a-zA-Z0-9_-]+|/Users/[a-zA-Z0-9_-]+)' -- "${PATH_EXCLUDES[@]}" 2>/dev/null || true)
if [ -n "$MATCHES" ]; then
    echo -e "${RED}  ❌ [PATH LEAK] Machine-bound user path detected in tracked files:${NC}"
    echo "$MATCHES" | while IFS= read -r LINE; do
        echo -e "     ${RED}$LINE${NC}"
    done
    CONTENT_LEAKS=$((CONTENT_LEAKS + 1))
    ERRORS=$((ERRORS + 1))
fi

# Check for GitHub Personal Access Tokens
TOKEN_MATCHES=$(git grep -nE 'ghp_[a-zA-Z0-9]{36}' -- "${PATH_EXCLUDES[@]}" 2>/dev/null || true)
if [ -n "$TOKEN_MATCHES" ]; then
    echo -e "${RED}  ❌ [TOKEN LEAK] GitHub PAT detected!${NC}"
    echo "$TOKEN_MATCHES" | while IFS= read -r LINE; do
        echo -e "     ${RED}$LINE${NC}"
    done
    CONTENT_LEAKS=$((CONTENT_LEAKS + 1))
    ERRORS=$((ERRORS + 1))
fi

# Check for Google API Keys
KEY_MATCHES=$(git grep -nE 'AIza[0-9A-Za-z_-]{35}' -- "${PATH_EXCLUDES[@]}" 2>/dev/null || true)
if [ -n "$KEY_MATCHES" ]; then
    echo -e "${RED}  ❌ [KEY LEAK] Google API key detected!${NC}"
    echo "$KEY_MATCHES" | while IFS= read -r LINE; do
        echo -e "     ${RED}$LINE${NC}"
    done
    CONTENT_LEAKS=$((CONTENT_LEAKS + 1))
    ERRORS=$((ERRORS + 1))
fi

# Check for Private Cryptographic Keys
PRIV_KEY_MATCHES=$(git grep -nE -- '-----BEGIN [A-Z ]*PRIVATE KEY-----' -- "${PATH_EXCLUDES[@]}" 2>/dev/null || true)
if [ -n "$PRIV_KEY_MATCHES" ]; then
    echo -e "${RED}  ❌ [KEY LEAK] Private cryptographic key detected!${NC}"
    echo "$PRIV_KEY_MATCHES" | while IFS= read -r LINE; do
        echo -e "     ${RED}$LINE${NC}"
    done
    CONTENT_LEAKS=$((CONTENT_LEAKS + 1))
    ERRORS=$((ERRORS + 1))
fi

# Check for Google Calendar IDs
CAL_MATCHES=$(git grep -nE '[a-zA-Z0-9._%+-]+@group\.calendar\.google\.com' -- "${PATH_EXCLUDES[@]}" 2>/dev/null || true)
if [ -n "$CAL_MATCHES" ]; then
    echo -e "${RED}  ❌ [CALENDAR LEAK] Google Calendar ID detected:${NC}"
    echo "$CAL_MATCHES" | while IFS= read -r LINE; do
        echo -e "     ${RED}$LINE${NC}"
    done
    CONTENT_LEAKS=$((CONTENT_LEAKS + 1))
    ERRORS=$((ERRORS + 1))
fi

# Check for Quarantined TaskNote filenames / dated paths
TASK_MATCHES=$(git grep -nE '(TaskNotes|chrysalis)/Tasks/202[0-9]{5}-[a-zA-Z0-9_-]+\.md' -- "${PATH_EXCLUDES[@]}" 2>/dev/null || true)
if [ -n "$TASK_MATCHES" ]; then
    echo -e "${RED}  ❌ [TASK LEAK] Quarantined task note path detected:${NC}"
    echo "$TASK_MATCHES" | while IFS= read -r LINE; do
        echo -e "     ${RED}$LINE${NC}"
    done
    CONTENT_LEAKS=$((CONTENT_LEAKS + 1))
    ERRORS=$((ERRORS + 1))
fi

if [ "$CONTENT_LEAKS" -eq 0 ]; then
    echo -e "${GREEN}  ✓ Zero machine paths, API keys, calendar IDs, or task paths found in tracked files.${NC}"
fi

# ------------------------------------------------------------------------------
# 3. Staged Changes Review (git diff --cached)
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[3/4] Inspecting staged changes in git index...${NC}"

CACHED_DIFF=$(git diff --cached 2>/dev/null || true)
if [ -n "$CACHED_DIFF" ]; then
    STAGED_LEAKS=0

    # Check for personal path additions in staged diff
    STAGED_PATH_ADDITIONS=$(echo "$CACHED_DIFF" | grep -E '^\+[^+]' | grep -E '(/home/[a-zA-Z0-9_-]+|/Users/[a-zA-Z0-9_-]+)' 2>/dev/null || true)
    if [ -n "$STAGED_PATH_ADDITIONS" ]; then
        echo -e "${RED}  ❌ [STAGED LEAK] Machine path staged in git diff:${NC}"
        echo -e "     $STAGED_PATH_ADDITIONS"
        STAGED_LEAKS=$((STAGED_LEAKS + 1))
        ERRORS=$((ERRORS + 1))
    fi

    # Check for Google Calendar ID additions in staged diff
    STAGED_CAL_ADDITIONS=$(echo "$CACHED_DIFF" | grep -E '^\+[^+]' | grep -E '@group\.calendar\.google\.com' 2>/dev/null || true)
    if [ -n "$STAGED_CAL_ADDITIONS" ]; then
        echo -e "${RED}  ❌ [STAGED LEAK] Google Calendar ID staged in git diff:${NC}"
        echo -e "     $STAGED_CAL_ADDITIONS"
        STAGED_LEAKS=$((STAGED_LEAKS + 1))
        ERRORS=$((ERRORS + 1))
    fi

    # Check for Quarantined TaskNote additions in staged diff
    STAGED_TASK_ADDITIONS=$(echo "$CACHED_DIFF" | grep -E '^\+[^+]' | grep -E '(TaskNotes|chrysalis)/Tasks/202[0-9]' 2>/dev/null || true)
    if [ -n "$STAGED_TASK_ADDITIONS" ]; then
        echo -e "${RED}  ❌ [STAGED LEAK] Quarantined task note path staged in git diff:${NC}"
        echo -e "     $STAGED_TASK_ADDITIONS"
        STAGED_LEAKS=$((STAGED_LEAKS + 1))
        ERRORS=$((ERRORS + 1))
    fi

    # Check for API Keys / Secrets additions in staged diff
    STAGED_SECRET_ADDITIONS=$(echo "$CACHED_DIFF" | grep -E '^\+[^+]' | grep -E '(ghp_[a-zA-Z0-9]{36}|AIza[0-9A-Za-z_-]{35}|-----BEGIN [A-Z ]*PRIVATE KEY-----)' 2>/dev/null || true)
    if [ -n "$STAGED_SECRET_ADDITIONS" ]; then
        echo -e "${RED}  ❌ [STAGED LEAK] Secret or credential staged in git diff:${NC}"
        echo -e "     $STAGED_SECRET_ADDITIONS"
        STAGED_LEAKS=$((STAGED_LEAKS + 1))
        ERRORS=$((ERRORS + 1))
    fi

    if [ "$STAGED_LEAKS" -eq 0 ]; then
        echo -e "${GREEN}  ✓ Staged diff contains no machine paths, calendar IDs, task paths, or secrets.${NC}"
    fi
else
    echo -e "${GREEN}  ✓ Git staging index is currently clean.${NC}"
fi

# ------------------------------------------------------------------------------
# 4. .gitignore Default-Deny Architecture Check
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}[4/4] Verifying .gitignore Default-Deny Architecture...${NC}"

if git grep -qE '^/\*$' -- .gitignore 2>/dev/null || grep -qE '^/\*$' .gitignore 2>/dev/null; then
    echo -e "${GREEN}  ✓ .gitignore enforces root default-deny (/*).${NC}"
else
    echo -e "${RED}  ❌ [SECURITY ERROR] .gitignore is missing root default-deny (/*)!${NC}"
    ERRORS=$((ERRORS + 1))
fi

# ------------------------------------------------------------------------------
# Final Verdict
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}=======================================================${NC}"
if [ "$ERRORS" -gt 0 ]; then
    echo -e "${RED}❌ AUDIT FAILED: $ERRORS violation(s) detected.${NC}"
    echo -e "${YELLOW}Please remediate all leaks before committing to GitHub.${NC}"
    exit 1
else
    echo -e "${GREEN}✅ AUDIT PASSED: No violations detected by these checks; review additions before publishing.${NC}"
    exit 0
fi
