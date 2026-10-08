"""Whole working-tree checks. Detailed reports belong outside source."""
import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import yaml

PRIVATE_PREFIXES = (".agent", ".agents", ".obsidian", ".venv", "node_modules", "Nexus", ".conversations", ".workspaces", ".trash")
PRIVATE_SYSTEM = {"Memory.md", "Life-Roadmap.md", "Integrations.md", "Ingestion-Sources.md", "System-Health.md", "Onboarding.md", "Changelog.md"}


def check(root=ROOT):
    root = Path(root).resolve()
    findings, files = [], []
    def issue(code, relative):
        findings.append({"code": code, "path": relative})
    def walk(directory):
        for path in sorted(directory.iterdir()):
            if path == root / ".git":
                continue
            relative = path.relative_to(root).as_posix()
            if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
                issue("redirected_source", relative)
                continue
            if path.is_dir():
                if path.name in PRIVATE_PREFIXES or path.name in {"__pycache__", ".pytest_cache", "backups", "archive"}:
                    issue("private_or_generated_directory", relative)
                walk(path)
            elif path.is_file():
                files.append(path)
    walk(root)
    brands = re.compile(r"antigravity|codex|claude\s+code", re.I)
    machine = re.compile(r"[a-z]:[\\/]+users[\\/]|/home/[a-z0-9_-]+/", re.I)
    secrets = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{25,}|AIza[A-Za-z0-9_-]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{30,}")
    for path in files:
        relative = path.relative_to(root).as_posix()
        parts = path.relative_to(root).parts
        if parts[0] in {"Daily", "Attachments", "Sources"}:
            issue("personal_collection_in_source", relative)
        if parts[:1] == ("System",) and len(parts) == 2 and path.name in PRIVATE_SYSTEM:
            issue("private_state_in_source", relative)
        if parts[:2] == ("TaskNotes", "Tasks") and path.name != "example-task.md":
            issue("private_task_in_source", relative)
        if parts[:1] == ("Projects",) and len(parts) > 1 and parts[1] not in {"README.md", "_templates"}:
            issue("private_project_in_source", relative)
        if parts[:1] == ("Slipbox",) and len(parts) > 1 and parts[1] not in {"README.md", "_templates"}:
            issue("private_knowledge_in_source", relative)
        if parts[:1] == ("Environments",) and len(parts) > 1 and parts[1] not in {"README.md", "_templates"}:
            issue("private_environment_in_source", relative)
        if path.suffix in {".pyc", ".sqlite", ".db", ".zip", ".lock", ".env", ".log"} and relative != "Development/requirements.lock":
            issue("private_or_generated_file", relative)
        if path.suffix not in {".py", ".md", ".json", ".yaml", ".yml", ".base", ".ts", ".mjs", ".txt", ".lock"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            issue("non_utf8_source", relative)
            continue
        if machine.search(text):
            issue("machine_bound_user_path", relative)
        if secrets.search(text):
            issue("credential_pattern", relative)
        if path.suffix == ".md" and brands.search(text):
            issue("retired_harness_documentation", relative)
        if path.suffix == ".py":
            try:
                ast.parse(text)
            except SyntaxError:
                issue("python_syntax", relative)
        if path.suffix == ".json":
            try:
                json.loads(text)
            except ValueError:
                issue("json_syntax", relative)
        if path.suffix in {".yaml", ".yml", ".base"} or (path.suffix == ".md" and text.startswith("---\n")):
            try:
                yaml.safe_load(text.split("---", 2)[1] if path.suffix == ".md" else text)
            except yaml.YAMLError:
                issue("yaml_syntax", relative)
        if path.suffix == ".md":
            for target in re.findall(r"(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)", text):
                target = target.strip("<>").split("#", 1)[0]
                if not target or "://" in target or target.startswith(("mailto:", "#")):
                    continue
                if not (path.parent / target).exists():
                    issue("broken_document_link", relative)
    for skill in (root / "skills").glob("*/SKILL.md"):
        for relative in re.findall(r"references/[a-z0-9-]+\.md", skill.read_text()):
            if not (skill.parent / relative).is_file():
                issue("missing_skill_reference", skill.relative_to(root).as_posix())
    manifest = json.loads((root / "package.json").read_text())
    for relative in manifest["files"]:
        if not (root / relative).exists():
            issue("missing_package_resource", relative)
    if not (root / ".gitignore").read_text().splitlines()[1:]:
        issue("missing_privacy_policy", ".gitignore")
    if "/*" not in (root / ".gitignore").read_text().splitlines():
        issue("missing_default_deny", ".gitignore")
    return {"status": "passed" if not findings else "failed", "files_checked": len(files), "findings": findings,
            "scope": "entire non-Git working tree; prose review and Git history are separate"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = check()
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
