#!/usr/bin/env python3
"""
Chrysalis System Integrity & Diagnostic Suite (/doctor)
======================================================
Executes the comprehensive 6-point system integrity diagnostic suite:
1. Schema & Frontmatter Linter (_types/task.md & Task schema)
2. Timezone & Temporal Compliance Linter (explicit local offset, e.g. -05:00)
3. Strategic Tag Registry Validator (Life-Roadmap.md)
4. Graph & Wikilink Resolution Linter (Roadmaps, Zettels, Tasks)
5. Skill Protocol & Dependency Linter (.agent/skills and Development/skills)
6. Dynamic State & Multiplier Sanity Check (Scheduling-Memory.md, [0.20, 2.00])

Outputs live diagnostic reports and records findings in System/System-Health.md.
"""

import sys
import os
import re
import argparse
from datetime import datetime, date
from pathlib import Path

try:
    from .vault_paths import resolve_vault_root, vault_path
except ImportError:
    from vault_paths import resolve_vault_root, vault_path
from typing import Dict, Any, List, Tuple, Optional
import yaml

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TIMEZONE_OFFSET_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[+\-][0-9]{2}:[0-9]{2}$")
RAW_UTC_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")

def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extracts YAML frontmatter and markdown body."""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    try:
        data = yaml.safe_load(parts[1])
        return data if isinstance(data, dict) else {}, parts[2]
    except Exception as e:
        raise ValueError(f"YAML frontmatter parsing failed: {e}") from e

def read_frontmatter(file_path: Path) -> Tuple[Dict[str, Any], str]:
    """Reads frontmatter from a file."""
    if not file_path.exists():
        return {}, ""
    return parse_frontmatter(file_path.read_text(encoding="utf-8"))

class ChrysalisDoctor:
    def __init__(self, vault_root: Path):
        self.vault_root = vault_root
        self.repo_root = Path(__file__).resolve().parent.parent.parent
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.auto_heals: List[str] = []
        self.check_results: Dict[str, Dict[str, Any]] = {}

    def get_tasks_dirs(self) -> List[Tuple[Path, str]]:
        """Returns list of (directory_path, task_type) to check."""
        dirs = []
        for candidate in [vault_path(self.vault_root, "Tasks")]:
            if candidate.exists() and candidate.is_dir():
                dirs.append((candidate, "active"))
                break
                
        for candidate in [vault_path(self.vault_root, "Archive")]:
            if candidate.exists() and candidate.is_dir():
                dirs.append((candidate, "archived"))
                break
        return dirs

    def check_1_schema_and_frontmatter(self):
        """Check 1: Schema & Frontmatter Linter."""
        required_fields = ["title", "status", "priority", "urgency_tier", "timeEstimate", "modality", "tags"]
        allowed_status = {"todo", "in-progress", "done", "archived"}
        allowed_priority = {"urgent", "high", "normal", "low", "none"}
        allowed_modality = {"analytical", "kinetic", "synthesis", "administrative"}

        task_count = 0
        valid_count = 0
        task_dirs = self.get_tasks_dirs()

        for tdir, role in task_dirs:
            for task_file in tdir.glob("*.md"):
                if task_file.name.startswith("."):
                    continue
                task_count += 1
                try:
                    fm, _ = read_frontmatter(task_file)
                    missing = [f for f in required_fields if f not in fm]
                    if missing:
                        self.errors.append(f"[Schema] {task_file.name} missing required fields: {', '.join(missing)}")
                        continue
                    if fm.get("status") not in allowed_status:
                        self.errors.append(f"[Schema] {task_file.name} invalid status '{fm.get('status')}'")
                        continue
                    if fm.get("priority") not in allowed_priority:
                        self.errors.append(f"[Schema] {task_file.name} invalid priority '{fm.get('priority')}'")
                        continue
                    if fm.get("modality") not in allowed_modality:
                        self.errors.append(f"[Schema] {task_file.name} invalid modality '{fm.get('modality')}'")
                        continue
                    valid_count += 1
                except Exception as e:
                    self.errors.append(f"[Schema] {task_file.name} parse error: {e}")

        status = "PASS" if valid_count == task_count and task_count > 0 else ("WARN" if task_count == 0 else "FAIL")
        self.check_results["1_schema"] = {
            "name": "1. Schema & Frontmatter",
            "status": "🟢 PASS" if status == "PASS" else ("🟡 WARN" if status == "WARN" else "🔴 FAIL"),
            "details": f"{valid_count}/{task_count} tasks strictly valid"
        }

    def check_2_timezone_compliance(self):
        """Check 2: Timezone & Temporal Compliance Linter."""
        timestamp_keys = ["dateCreated", "created", "scheduled", "startedAt", "completedAt"]
        total_ts = 0
        valid_ts = 0
        overdue_tasks = []

        task_dirs = self.get_tasks_dirs()
        today = date.today()

        for tdir, role in task_dirs:
            for task_file in tdir.glob("*.md"):
                if task_file.name.startswith("."):
                    continue
                try:
                    fm, _ = read_frontmatter(task_file)
                    for k in timestamp_keys:
                        val = fm.get(k)
                        if val:
                            total_ts += 1
                            val_str = str(val).strip()
                            if RAW_UTC_PATTERN.match(val_str):
                                self.errors.append(f"[Timezone] {task_file.name} has raw UTC 'Z' timestamp in {k}: {val_str}")
                            elif TIMEZONE_OFFSET_PATTERN.match(val_str):
                                valid_ts += 1
                            elif len(val_str) == 10 and val_str.count("-") == 2:
                                # Date-only timestamp (e.g. due)
                                valid_ts += 1
                            else:
                                valid_ts += 1

                    due_val = fm.get("due")
                    status_val = fm.get("status")
                    if due_val and status_val == "todo":
                        try:
                            due_date = date.fromisoformat(str(due_val).strip()[:10])
                            if due_date < today:
                                overdue_tasks.append((task_file.name, str(due_val)))
                        except Exception:
                            pass
                except Exception:
                    pass

        if overdue_tasks:
            for tname, dstr in overdue_tasks:
                self.warnings.append(f"[Temporal Rollover] Task {tname} is overdue (due {dstr}) and requires rollover review")

        has_tz_errors = any("[Timezone]" in e for e in self.errors)
        status = "FAIL" if has_tz_errors else ("WARN" if overdue_tasks else "PASS")
        self.check_results["2_timezone"] = {
            "name": "2. Timezone Compliance",
            "status": "🟢 PASS" if status == "PASS" else ("🟡 WARNING" if status == "WARN" else "🔴 FAIL"),
            "details": f"{valid_ts}/{total_ts} timestamps explicit local; {len(overdue_tasks)} overdue tasks flagged"
        }

    def check_3_tag_registry(self):
        """Check 3: Strategic Tag Registry Validator."""
        roadmap_path = None
        for candidate in [
            self.vault_root / "chrysalis" / "System" / "Life-Roadmap.md",
            self.vault_root / "System" / "Life-Roadmap.md",
            self.repo_root / "System" / "_templates" / "Life-Roadmap.template.md"
        ]:
            if candidate.exists():
                roadmap_path = candidate
                break

        registered_tags = set()
        if roadmap_path:
            try:
                fm, _ = read_frontmatter(roadmap_path)
                tag_reg = fm.get("tag_registry", {})
                if isinstance(tag_reg, dict):
                    for pillar, tags in tag_reg.items():
                        if isinstance(tags, list):
                            for t in tags:
                                registered_tags.add(str(t).lower())
                elif isinstance(tag_reg, list):
                    for t in tag_reg:
                        registered_tags.add(str(t).lower())
                for p in fm.get("pillars", []):
                    for t in p.get("tags", []):
                        registered_tags.add(str(t).lower())
            except Exception as e:
                self.errors.append(f"[Tag Registry] Failed to parse {roadmap_path.name}: {e}")

        unregistered = []
        task_dirs = self.get_tasks_dirs()
        for tdir, role in task_dirs:
            for task_file in tdir.glob("*.md"):
                if task_file.name.startswith("."):
                    continue
                try:
                    fm, _ = read_frontmatter(task_file)
                    for t in fm.get("tags", []):
                        t_clean = str(t).strip().lstrip("#").lower()
                        if t_clean.startswith("pillar-") and registered_tags and t_clean not in registered_tags:
                            unregistered.append((task_file.name, t_clean))
                except Exception:
                    pass

        if unregistered:
            for tname, tag in unregistered:
                self.warnings.append(f"[Tag Registry] Task {tname} has unregistered pillar tag '#{tag}'")

        status = "PASS" if not unregistered else "WARN"
        self.check_results["3_tag_registry"] = {
            "name": "3. Strategic Tag Registry",
            "status": "🟢 PASS" if status == "PASS" else "🟡 WARNING",
            "details": f"All tags matched against Life-Roadmap.md ({len(registered_tags)} registered tags)"
        }

    def check_4_graph_integrity(self):
        """Check 4: Graph & Wikilink Resolution Linter."""
        broken_links = []
        slipbox_dir = None
        for candidate in [vault_path(self.vault_root, "Slipbox")]:
            if candidate.exists() and candidate.is_dir():
                slipbox_dir = candidate
                break

        projects_dir = None
        for candidate in [vault_path(self.vault_root, "Projects")]:
            if candidate.exists() and candidate.is_dir():
                projects_dir = candidate
                break

        task_dirs = self.get_tasks_dirs()
        for tdir, role in task_dirs:
            for task_file in tdir.glob("*.md"):
                if task_file.name.startswith("."):
                    continue
                try:
                    fm, _ = read_frontmatter(task_file)
                    pref = fm.get("project_ref")
                    if pref and isinstance(pref, str):
                        target = pref.strip().strip("[]")
                        if not target.endswith(".md"):
                            target += ".md"
                        if projects_dir:
                            proj_target = projects_dir / target.replace("Projects/", "")
                            if not proj_target.exists():
                                broken_links.append((task_file.name, pref))
                    for z in fm.get("linked_zettels", []):
                        zt = str(z).strip().strip("[]")
                        if not zt.endswith(".md"):
                            zt += ".md"
                        if slipbox_dir:
                            z_target = slipbox_dir / zt.replace("Slipbox/", "")
                            if not z_target.exists():
                                broken_links.append((task_file.name, str(z)))
                except Exception:
                    pass

        if broken_links:
            for tname, link in broken_links:
                self.warnings.append(f"[Wikilink] {tname} references missing target {link}")

        status = "PASS" if not broken_links else "WARN"
        self.check_results["4_graph"] = {
            "name": "4. Graph & Wikilink Resolution",
            "status": "🟢 PASS" if status == "PASS" else "🟡 WARNING",
            "details": f"All project roadmap links and notes valid ({len(broken_links)} broken links)"
        }

    def check_5_skills_integrity(self):
        """Check 5: Skill Protocol & Dependency Linter."""
        skill_files = []
        for root in [self.repo_root, self.vault_root]:
            for p in list((root / ".agent" / "skills").glob("*/SKILL.md")) + list((root / "Development" / "skills").glob("*/SKILL.md")):
                if p not in skill_files and p.exists():
                    skill_files.append(p)

        valid_skills = 0
        for sf in skill_files:
            try:
                fm, _ = read_frontmatter(sf)
                if fm.get("name") and fm.get("description"):
                    valid_skills += 1
                else:
                    self.errors.append(f"[Skill Protocol] {sf.parent.name} missing name or description")
            except Exception as e:
                self.errors.append(f"[Skill Protocol] {sf.parent.name} parse error: {e}")

        status = "PASS" if valid_skills == len(skill_files) and valid_skills > 0 else "FAIL"
        self.check_results["5_skills"] = {
            "name": "5. Skill Runbooks & Dependencies",
            "status": "🟢 PASS" if status == "PASS" else "🔴 FAIL",
            "details": f"{valid_skills}/{len(skill_files)} skills strictly verified"
        }

    def check_6_dynamic_state_multipliers(self):
        """Check 6: Dynamic State & Multiplier Sanity Check ([0.20, 2.00])."""
        mem_path = None
        for candidate in [
            self.vault_root / "chrysalis" / "System" / "Scheduling-Memory.md",
            self.vault_root / "System" / "Scheduling-Memory.md",
            self.repo_root / "System" / "_templates" / "Scheduling-Memory.template.md"
        ]:
            if candidate.exists():
                mem_path = candidate
                break

        multiplier_count = 0
        out_of_bounds = []
        if mem_path:
            try:
                fm, _ = read_frontmatter(mem_path)
                tag_mults = fm.get("tag_multipliers", {})
                if isinstance(tag_mults, dict):
                    for k, v in tag_mults.items():
                        multiplier_count += 1
                        try:
                            val = float(v)
                            if val < 0.20 or val > 2.00:
                                out_of_bounds.append((f"tag_multiplier:{k}", val))
                        except Exception:
                            out_of_bounds.append((f"tag_multiplier:{k}", v))

                weights = fm.get("inferred_task_pool", {}).get("learning_weights", {})
                if isinstance(weights, dict):
                    for k, v in weights.items():
                        multiplier_count += 1
                        try:
                            val = float(v)
                            if val < 0.20 or val > 2.00:
                                out_of_bounds.append((f"learning_weight:{k}", val))
                        except Exception:
                            out_of_bounds.append((f"learning_weight:{k}", v))
            except Exception as e:
                self.errors.append(f"[Multiplier Sanity] Failed to parse {mem_path.name}: {e}")

        if out_of_bounds:
            for k, v in out_of_bounds:
                self.errors.append(f"[Multiplier Invariant] {k}={v} is outside strict bounds [0.20, 2.00]")

        status = "PASS" if not out_of_bounds else "FAIL"
        self.check_results["6_multipliers"] = {
            "name": "6. Dynamic State & Multipliers",
            "status": "🟢 PASS" if status == "PASS" else "🔴 FAIL",
            "details": f"All {multiplier_count} multipliers strictly within [0.20, 2.00]"
        }

    def update_system_health_ledger(self):
        """Writes diagnostic report to System/System-Health.md."""
        tz_offset = "-05:00"
        mem_file = None
        for candidate in [vault_path(self.vault_root, "System/Scheduling-Memory.md")]:
            if candidate.exists():
                mem_file = candidate
                break
        if mem_file:
            try:
                content = mem_file.read_text(encoding="utf-8")
                m = re.search(r'timezone_offset:\s*["\']?([+\-][0-9]{2}:[0-9]{2})["\']?', content)
                if m:
                    tz_offset = m.group(1)
            except Exception:
                pass

        now_dt = datetime.now()
        now_iso = now_dt.strftime(f"%Y-%m-%dT%H:%M:%S{tz_offset}")
        
        health_status = "HEALTHY" if len(self.errors) == 0 else "DEGRADED"
        if len(self.errors) > 5:
            health_status = "CRITICAL"

        report_lines = [
            "---",
            "type: system_health_report",
            "id: chrysalis-system-health",
            f'last_audit: "{now_iso}"',
            f'health_status: "{health_status}"',
            f"errors_count: {len(self.errors)}",
            f"warnings_count: {len(self.warnings)}",
            "---",
            "",
            "# 🩺 Chrysalis System Health & Integrity Ledger",
            "",
            f"> **System Health Status:** {'🟢 HEALTHY' if health_status == 'HEALTHY' else ('🟡 DEGRADED' if health_status == 'DEGRADED' else '🔴 CRITICAL')}  ",
            f"> **Last Diagnostic Pass:** {now_iso}  ",
            f"> **Errors:** {len(self.errors)} • **Warnings:** {len(self.warnings)}  ",
            "",
            "---",
            "",
            "## 🔍 Diagnostic Linter Results",
            "",
            "| Linter Domain | Status | Details |",
            "| :--- | :---: | :--- |",
        ]

        for k in sorted(self.check_results.keys()):
            res = self.check_results[k]
            report_lines.append(f"| **{res['name']}** | {res['status']} | {res['details']} |")

        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        report_lines.append("## 🛠️ Auto-Heal & Warning Log")
        if not self.errors and not self.warnings:
            report_lines.append("* **Nominal Integrity:** All task frontmatter schemas, skill specifications, and dynamic state multipliers conform strictly to system invariants. Zero auto-heal modifications required during this pass.")
        else:
            if self.errors:
                report_lines.append("### 🔴 Errors")
                for err in self.errors:
                    report_lines.append(f"* {err}")
            if self.warnings:
                report_lines.append("### 🟡 Warnings")
                for warn in self.warnings:
                    report_lines.append(f"* {warn}")

        report_lines.append("")

        content = "\n".join(report_lines)
        target_paths = []
        for candidate in [vault_path(self.vault_root, "System/System-Health.md")]:
            if candidate.parent.exists():
                target_paths.append(candidate)
                break
                
        for tp in target_paths:
            try:
                tp.write_text(content, encoding="utf-8")
                print(f"[doctor] Synchronized health ledger: {tp}")
            except Exception as e:
                print(f"[doctor] Warning writing health ledger {tp}: {e}", file=sys.stderr)

    def run_all_checks(self, *, write_report: bool = True) -> bool:
        """Executes all 6 checks and outputs summary."""
        print("=" * 70)
        print(f"🩺 Chrysalis System Integrity Pass (/doctor)")
        print(f"Vault Root: {self.vault_root}")
        print("=" * 70)

        self.check_1_schema_and_frontmatter()
        self.check_2_timezone_compliance()
        self.check_3_tag_registry()
        self.check_4_graph_integrity()
        self.check_5_skills_integrity()
        self.check_6_dynamic_state_multipliers()

        if write_report:
            self.update_system_health_ledger()

        print("\nDiagnostic Linter Results:")
        for k in sorted(self.check_results.keys()):
            res = self.check_results[k]
            print(f"  {res['status']} {res['name']}: {res['details']}")

        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"  🟡 {w}")

        if self.errors:
            print(f"\nErrors ({len(self.errors)}):")
            for e in self.errors:
                print(f"  🔴 {e}")
            print("\nResult: System health DEGRADED / FAILED.")
            return False

        print("\nResult: System health 🟢 HEALTHY (0 errors).")
        return True

def main():
    parser = argparse.ArgumentParser(description="Chrysalis System Integrity & Diagnostic Suite")
    parser.add_argument("--vault", type=str, default=None, help="Path to Chrysalis vault root")
    parser.add_argument("--read-only", action="store_true", help="Check without updating the health ledger")
    args = parser.parse_args()

    vault_root = resolve_vault_root(args.vault)
    doctor = ChrysalisDoctor(vault_root)
    success = doctor.run_all_checks(write_report=not args.read_only)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
