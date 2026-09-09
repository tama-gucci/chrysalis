#!/usr/bin/env python3
"""
Chrysalis Autonomous Zettelkasten Hypergraph Linker
==================================================
Connects the Chrysalis Tripartite Knowledge-Execution Continuum:
1. Knowledge Layer: Slipbox/*.md (Zettelkasten atomic insights)
2. Strategic Layer: Projects/*/Roadmap.md (Section 3: Reference Files & Contacts)
3. Execution Layer: TaskNotes/Tasks/*.md (linked_zettels frontmatter array)

Can be executed standalone via CLI or invoked programmatically during
/audit, /evening, or /zettel skill runs.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import yaml
except ImportError:
    yaml = None


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extracts frontmatter dict and markdown body from file content."""
    trimmed = content.lstrip()
    if not trimmed.startswith("---"):
        return {}, content

    end_idx = trimmed.find("\n---", 3)
    if end_idx == -1:
        return {}, content

    frontmatter_raw = trimmed[3:end_idx].strip()
    body = trimmed[end_idx + 4 :].lstrip("\r\n")

    if yaml:
        try:
            data = yaml.safe_load(frontmatter_raw)
            if isinstance(data, dict):
                return data, body
        except Exception:
            pass

    # Simple fallback parser if PyYAML is unavailable or malformed
    data = {}
    for line in frontmatter_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"\'')
            data[key] = val
    return data, body


def extract_wikilinks(text: str) -> List[str]:
    """Extracts target wikilinks [[Target]] from text."""
    return re.findall(r"\[\[(.*?)\]\]", text)


def normalize_tag(tag: str) -> str:
    """Normalizes tags by stripping leading '#' and converting to lowercase."""
    return tag.strip().lstrip("#").lower()


class ZettelGraphLinker:
    def __init__(self, vault_root: Optional[Path] = None):
        if vault_root:
            self.vault_root = Path(vault_root).resolve()
        elif "CHRYSALIS_VAULT_PATH" in os.environ:
            self.vault_root = Path(os.environ["CHRYSALIS_VAULT_PATH"]).resolve()
        else:
            # Fallback: traverse up from this script (System/scripts/ -> chrysalis)
            self.vault_root = Path(__file__).resolve().parent.parent.parent

    def scan_zettels(self) -> List[Dict[str, Any]]:
        """Scans Slipbox/*.md for atomic notes, excluding templates and READMEs."""
        slipbox_dir = None
        for candidate in [self.vault_root / "Slipbox", self.vault_root / "chrysalis" / "Slipbox"]:
            if candidate.exists():
                slipbox_dir = candidate
                break
        if not slipbox_dir:
            return []

        zettels = []
        for file_path in slipbox_dir.glob("*.md"):
            if file_path.name == "README.md" or ".template." in file_path.name:
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
                fm, body = parse_frontmatter(content)
                tags = fm.get("tags", [])
                if isinstance(tags, str):
                    tags = [tags]
                norm_tags = [normalize_tag(str(t)) for t in tags]

                title = fm.get("title") or file_path.stem
                zettel_id = str(fm.get("id") or file_path.stem.split("-")[0])

                zettels.append({
                    "path": file_path,
                    "stem": file_path.stem,
                    "id": zettel_id,
                    "title": title,
                    "tags": norm_tags,
                    "body_links": extract_wikilinks(body),
                    "content": content,
                })
            except Exception as e:
                print(f"[zettel_graph_linker] Warning: Failed to read {file_path}: {e}", file=sys.stderr)

        return zettels

    def scan_projects(self) -> List[Dict[str, Any]]:
        """Scans Projects/*/Roadmap.md for project definitions."""
        projects_dir = None
        for candidate in [self.vault_root / "Projects", self.vault_root / "chrysalis" / "Projects"]:
            if candidate.exists():
                projects_dir = candidate
                break
        if not projects_dir:
            return []

        projects = []
        for roadmap_path in projects_dir.glob("*/Roadmap.md"):
            if ".template." in str(roadmap_path):
                continue
            try:
                content = roadmap_path.read_text(encoding="utf-8")
                fm, body = parse_frontmatter(content)
                tags = fm.get("tags", [])
                if isinstance(tags, str):
                    tags = [tags]
                norm_tags = [normalize_tag(str(t)) for t in tags]

                project_id = fm.get("project_id") or roadmap_path.parent.name
                pillar = normalize_tag(str(fm.get("pillar", "")))
                if pillar:
                    norm_tags.append(pillar)

                title = fm.get("title") or roadmap_path.parent.name
                status = fm.get("status", "active")

                # Extract Section 3 reference links
                sec3_match = re.search(r"(##\s+3\.\s+[^\n]+)([\s\S]*?)(?:---|\Z)", content)
                sec3_text = sec3_match.group(2) if sec3_match else ""
                existing_links = set(extract_wikilinks(sec3_text))

                projects.append({
                    "path": roadmap_path,
                    "folder_name": roadmap_path.parent.name,
                    "project_id": str(project_id).lower(),
                    "title": title,
                    "pillar": pillar,
                    "status": status,
                    "tags": norm_tags,
                    "existing_links": existing_links,
                    "content": content,
                })
            except Exception as e:
                print(f"[zettel_graph_linker] Warning: Failed to read {roadmap_path}: {e}", file=sys.stderr)

        return projects

    def scan_tasks(self) -> List[Dict[str, Any]]:
        """Scans Tasks/*.md or TaskNotes/Tasks/*.md for active tasks."""
        tasks_dir = None
        for candidate in [
            self.vault_root / "Tasks",
            self.vault_root / "chrysalis" / "Tasks",
            self.vault_root / "TaskNotes" / "Tasks",
        ]:
            if candidate.exists():
                tasks_dir = candidate
                break
        if not tasks_dir:
            return []

        tasks = []
        for task_path in tasks_dir.glob("*.md"):
            if task_path.name == "README.md" or ".template." in task_path.name:
                continue
            try:
                content = task_path.read_text(encoding="utf-8")
                fm, body = parse_frontmatter(content)

                tags = fm.get("tags", [])
                if isinstance(tags, str):
                    tags = [tags]
                norm_tags = [normalize_tag(str(t)) for t in tags]

                project_ref = fm.get("project_ref")
                if project_ref and str(project_ref).lower() != "null":
                    project_ref = str(project_ref).strip('"\'')
                else:
                    project_ref = None

                linked_zettels = fm.get("linked_zettels") or []
                if isinstance(linked_zettels, str):
                    linked_zettels = [linked_zettels]
                clean_zettels = [str(z).strip('"\'') for z in linked_zettels]

                tasks.append({
                    "path": task_path,
                    "title": fm.get("title") or task_path.stem,
                    "status": fm.get("status", "todo"),
                    "tags": norm_tags,
                    "project_ref": project_ref,
                    "linked_zettels": clean_zettels,
                    "content": content,
                })
            except Exception as e:
                print(f"[zettel_graph_linker] Warning: Failed to read {task_path}: {e}", file=sys.stderr)

        return tasks

    def match_zettel_to_project(self, zettel: Dict[str, Any], project: Dict[str, Any]) -> bool:
        """Determines if a Zettel note relates to a project."""
        # 1. Check explicit wikilinks in body
        zettel_links = zettel.get("body_links", [])
        proj_folder = project["folder_name"].lower()
        proj_id = project["project_id"].lower()
        for link in zettel_links:
            clean_link = link.lower()
            if proj_folder in clean_link or proj_id in clean_link:
                return True

        # 2. Check tag intersection
        z_tags = set(zettel.get("tags", []))
        p_tags = set(project.get("tags", []))
        if z_tags.intersection(p_tags):
            return True

        # 3. Check tag prefixes & hierarchy (e.g. pillar-1 matches pillar-1/setup or chrysalis matches chrysalis/habit)
        for zt in z_tags:
            for pt in p_tags:
                if zt == pt:
                    return True
                if zt.startswith(f"{pt}/") or pt.startswith(f"{zt}/"):
                    return True

        # 4. Check project ID & folder tokens against non-generic zettel tags
        generic_tags = {"zettel", "template", "task"}
        proj_tokens = set(re.split(r"[-_/\s]+", f"{proj_id} {proj_folder} {project.get('title', '').lower()}"))
        proj_tokens.discard("")

        for zt in z_tags:
            if zt in generic_tags:
                continue
            zt_components = set(re.split(r"[-_/\s]+", zt))
            zt_components.discard("")
            if zt_components.intersection(proj_tokens):
                return True

        # 5. Check if project content references the zettel
        proj_content = project.get("content", "").lower()
        if zettel["stem"].lower() in proj_content or zettel["id"].lower() in proj_content:
            return True

        return False

    def link_hypergraph(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Executes bidirectional linking:
        1. Links Zettels to Projects (under Section 3)
        2. Links Zettels to matching Tasks (in linked_zettels frontmatter)
        """
        zettels = self.scan_zettels()
        projects = self.scan_projects()
        tasks = self.scan_tasks()

        project_updates = []
        task_updates = []

        # 1. Project Roadmaps <- Zettels
        for proj in projects:
            matched_zettels = []
            for zet in zettels:
                if self.match_zettel_to_project(zet, proj):
                    matched_zettels.append(zet)

            if not matched_zettels:
                continue

            links_to_add = []
            for zet in matched_zettels:
                stem = zet["stem"]
                wikilink = f"[[{stem}]]"
                # Check if already present as stem or id
                if stem not in proj["existing_links"] and zet["id"] not in proj["existing_links"]:
                    links_to_add.append((wikilink, zet["title"]))

            if links_to_add:
                project_updates.append({
                    "project": proj["title"],
                    "path": str(proj["path"]),
                    "new_links": [l[0] for l in links_to_add],
                })
                if not dry_run:
                    self._append_links_to_project(proj["path"], links_to_add)

        # 2. Tasks <- Zettels (via project reference or tag match)
        for task in tasks:
            candidate_zettels: Set[str] = set()

            # Find matching project for task
            for proj in projects:
                task_belongs_to_proj = False
                if task["project_ref"]:
                    clean_ref = task["project_ref"].lower()
                    if (
                        proj["project_id"] in clean_ref
                        or proj["folder_name"].lower() in clean_ref
                        or proj["title"].lower() in clean_ref
                    ):
                        task_belongs_to_proj = True
                else:
                    # Tag overlap
                    if set(task["tags"]).intersection(set(proj["tags"])):
                        task_belongs_to_proj = True

                if task_belongs_to_proj:
                    for zet in zettels:
                        if self.match_zettel_to_project(zet, proj):
                            candidate_zettels.add(f"[[{zet['stem']}]]")

            # Also check direct task tag match with zettel
            for zet in zettels:
                if set(task["tags"]).intersection(set(zet["tags"])):
                    candidate_zettels.add(f"[[{zet['stem']}]]")

            # Determine new zettels to add
            current_zettels = set(task["linked_zettels"])
            new_zettels = candidate_zettels - current_zettels

            if new_zettels:
                updated_list = sorted(list(current_zettels.union(new_zettels)))
                task_updates.append({
                    "task": task["title"],
                    "path": str(task["path"]),
                    "added_zettels": sorted(list(new_zettels)),
                    "total_zettels": len(updated_list),
                })
                if not dry_run:
                    self._update_task_frontmatter_zettels(task["path"], updated_list)

        return {
            "vault_root": str(self.vault_root),
            "zettels_scanned": len(zettels),
            "projects_scanned": len(projects),
            "tasks_scanned": len(tasks),
            "projects_updated": len(project_updates),
            "tasks_updated": len(task_updates),
            "project_details": project_updates,
            "task_details": task_updates,
            "dry_run": dry_run,
        }

    def _append_links_to_project(self, project_path: Path, links: List[Tuple[str, str]]) -> None:
        """Appends [[WikiLink]] entries to Section 3 of a project roadmap."""
        content = project_path.read_text(encoding="utf-8")
        sec3_match = re.search(r"(##\s+3\.\s+[^\n]+)", content)
        if not sec3_match:
            # If Section 3 doesn't exist, append it at the end
            lines_to_add = "\n\n---\n\n## 3. Reference Files & Contacts\n"
            for link, title in links:
                lines_to_add += f"- {link} # {title}\n"
            content += lines_to_add
        else:
            header_str = sec3_match.group(1)
            pos = content.find(header_str) + len(header_str)
            # Find next newline
            nl_pos = content.find("\n", pos)
            insert_pos = nl_pos + 1 if nl_pos != -1 else pos

            formatted_links = "\n"
            for link, title in links:
                formatted_links += f"- {link} # {title}\n"

            content = content[:insert_pos] + formatted_links + content[insert_pos:]

        project_path.write_text(content, encoding="utf-8")

    def _update_task_frontmatter_zettels(self, task_path: Path, zettels: List[str]) -> None:
        """Updates the linked_zettels array in a task note's frontmatter."""
        content = task_path.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)

        in_fm = False
        out_lines = []
        in_zettel_block = False

        zettel_block_lines = ["linked_zettels:\n"]
        if not zettels:
            zettel_block_lines = ["linked_zettels: []\n"]
        else:
            for z in zettels:
                clean = z.strip('"\'')
                zettel_block_lines.append(f'  - "{clean}"\n')

        has_written_zettels = False

        for line in lines:
            stripped = line.strip()
            if stripped == "---":
                if not in_fm:
                    in_fm = True
                    out_lines.append(line)
                    continue
                else:
                    # Closing frontmatter
                    if in_fm and not has_written_zettels:
                        out_lines.extend(zettel_block_lines)
                        has_written_zettels = True
                    in_fm = False
                    in_zettel_block = False
                    out_lines.append(line)
                    continue

            if in_fm:
                if line.startswith("linked_zettels:"):
                    in_zettel_block = True
                    out_lines.extend(zettel_block_lines)
                    has_written_zettels = True
                    continue

                if in_zettel_block:
                    if line.startswith("  -") or line.strip() == "[]":
                        continue
                    else:
                        in_zettel_block = False

            out_lines.append(line)

        task_path.write_text("".join(out_lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Chrysalis Autonomous Zettelkasten Hypergraph Linker")
    parser.add_argument("--vault", type=str, default=None, help="Path to Chrysalis vault root")
    parser.add_argument("--dry-run", action="store_true", help="Simulate linking without writing changes to disk")
    parser.add_argument("--sync", action="store_true", help="Execute physical mutations to disk (anti-simulation law)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    dry_run = args.dry_run or (not args.sync)

    vault_path = Path(args.vault) if args.vault else None
    linker = ZettelGraphLinker(vault_root=vault_path)
    result = linker.link_hypergraph(dry_run=dry_run)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        mode_str = "🔍 DRY-RUN MODE (No disk mutations)" if dry_run else "⚡ SYNC MODE (Physical mutations persisted)"
        print(f"=== Chrysalis Zettelkasten Hypergraph Linker ({mode_str}) ===")
        print(f"Vault Root:        {result['vault_root']}")
        print(f"Slipbox Zettels:   {result['zettels_scanned']}")
        print(f"Projects Scanned:  {result['projects_scanned']}")
        print(f"Tasks Scanned:     {result['tasks_scanned']}")
        print(f"Projects Updated:  {result['projects_updated']}")
        print(f"Tasks Updated:     {result['tasks_updated']}")

        if result["project_details"]:
            print("\nProject Updates:")
            for p in result["project_details"]:
                print(f"  • {p['project']}: added {p['new_links']}")

        if result["task_details"]:
            print("\nTask Updates:")
            for t in result["task_details"]:
                print(f"  • {t['task']}: added {t['added_zettels']} (total: {t['total_zettels']})")


if __name__ == "__main__":
    main()
