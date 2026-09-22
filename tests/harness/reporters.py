"""
tests/harness/reporters.py
Diagnostic and Summary Reporters for Chrysalis Validation Harness.
Supports Terminal ANSI, JSON, TAP v13, and Markdown formats.
"""
import json
from typing import Any, Dict, List, Optional
from .models import (
    Diagnostic,
    DiagnosticSeverity,
    ValidationLayer,
    ValidationReport,
)

# ANSI Color Codes
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_RED = "\033[31m"
COLOR_GREEN = "\033[32m"
COLOR_YELLOW = "\033[33m"
COLOR_BLUE = "\033[34m"
COLOR_CYAN = "\033[36m"


class BaseReporter:
    def format_report(self, report: ValidationReport, use_color: bool = True) -> str:
        raise NotImplementedError


class TerminalReporter(BaseReporter):
    def format_report(self, report: ValidationReport, use_color: bool = True) -> str:
        c_reset = COLOR_RESET if use_color else ""
        c_bold = COLOR_BOLD if use_color else ""
        c_red = COLOR_RED if use_color else ""
        c_green = COLOR_GREEN if use_color else ""
        c_yellow = COLOR_YELLOW if use_color else ""
        c_cyan = COLOR_CYAN if use_color else ""

        lines = [
            f"{c_bold}================================================================================{c_reset}",
            f"{c_bold}{c_cyan}CHRYSALIS MDBASE v0.3 LOCAL VALIDATION HARNESS{c_reset}",
            f"Collection Root: {report.collection_dir}",
            f"{c_bold}================================================================================{c_reset}",
        ]

        # Status lines per layer
        l1_status = f"{c_green}PASS{c_reset}" if report.layer1_errors == 0 else f"{c_red}FAIL ({report.layer1_errors} errors){c_reset}"
        l2_status = f"{c_green}PASS{c_reset}" if report.layer2_errors == 0 else f"{c_red}FAIL ({report.layer2_errors} errors){c_reset}"
        l3_status = f"{c_green}PASS{c_reset}" if report.layer3_errors == 0 else f"{c_red}FAIL ({report.layer3_errors} errors){c_reset}"

        lines.append(f"Layer 1 (Artifact Syntax & Schema) : {l1_status}")
        lines.append(f"Layer 2 (mdbase Engine Semantics)  : {l2_status}")
        lines.append(f"Layer 3 (Framework Behavior & Graph): {l3_status}")
        lines.append("--------------------------------------------------------------------------------")
        lines.append(f"{c_bold}Scan Summary:{c_reset}")
        type_str = ", ".join([f"{count} {t.capitalize()}s" for t, count in report.records_by_type.items()]) or "0 records"
        lines.append(f"  - Total Records Scanned: {report.total_files_scanned} ({type_str})")
        lines.append(f"  - Validation Duration  : {round(report.duration_seconds, 4)}s")

        total_errors = report.layer1_errors + report.layer2_errors + report.layer3_errors
        overall_status = f"{c_green}PASSED{c_reset}" if total_errors == 0 else f"{c_red}FAILED{c_reset}"
        lines.append(f"  - Overall Status       : {overall_status} ({total_errors} errors, {report.warnings} warnings)")

        if report.diagnostics:
            lines.append("--------------------------------------------------------------------------------")
            lines.append(f"{c_bold}Diagnostics:{c_reset}")
            for d in report.diagnostics:
                sev_color = c_red if str(d.severity) == "error" else (c_yellow if str(d.severity) == "warning" else c_cyan)
                loc_info = f" [{d.path or 'collection'}" + (f":{d.field}" if d.field else "") + "]"
                action_info = f" (Action: {d.recovery_action})" if d.recovery_action else ""
                lines.append(f"  {sev_color}[{str(d.severity).upper()}]{c_reset} {d.code}{loc_info}: {d.message}{action_info}")

        lines.append(f"{c_bold}================================================================================{c_reset}")
        return "\n".join(lines)


class JSONReporter(BaseReporter):
    def format_report(self, report: ValidationReport, use_color: bool = False) -> str:
        return json.dumps(report.to_dict(), indent=2)


class TAPReporter(BaseReporter):
    def format_report(self, report: ValidationReport, use_color: bool = False) -> str:
        lines = [
            "TAP version 13",
            f"1..{max(report.total_files_scanned, 1)}"
        ]
        if report.total_files_scanned == 0:
            lines.append("ok 1 - No record files scanned # SKIP empty collection")
        else:
            # We list summary ok lines
            i = 1
            for rec_type, count in report.records_by_type.items():
                for idx in range(count):
                    lines.append(f"ok {i} - {rec_type} item {idx + 1}")
                    i += 1

        total_errors = report.layer1_errors + report.layer2_errors + report.layer3_errors
        lines.append(f"# Summary: {report.total_files_scanned} files, {total_errors} errors, {report.warnings} warnings")
        for diag in report.diagnostics:
            lines.append(f"# [{str(diag.severity).upper()}] {diag.code} in {diag.path or 'collection'}: {diag.message}")
        return "\n".join(lines)


class MarkdownReporter(BaseReporter):
    def format_report(self, report: ValidationReport, use_color: bool = False) -> str:
        total_errors = report.layer1_errors + report.layer2_errors + report.layer3_errors
        status_badge = "✅ PASSED" if total_errors == 0 else "❌ FAILED"
        lines = [
            "# Chrysalis mdbase v0.3 Validation Report",
            "",
            f"- **Collection Root**: `{report.collection_dir}`",
            f"- **Status**: {status_badge}",
            f"- **Total Records**: {report.total_files_scanned}",
            f"- **Errors**: {total_errors} (Layer 1: {report.layer1_errors}, Layer 2: {report.layer2_errors}, Layer 3: {report.layer3_errors})",
            f"- **Warnings**: {report.warnings}",
            f"- **Duration**: {round(report.duration_seconds, 4)}s",
            "",
            "## Records By Type",
            "",
            "| Type | Count |",
            "| :--- | :--- |",
        ]
        for t, count in report.records_by_type.items():
            lines.append(f"| `{t}` | {count} |")

        if report.diagnostics:
            lines.extend([
                "",
                "## Diagnostics",
                "",
                "| Severity | Code | Layer | Path | Field | Message | Action |",
                "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
            ])
            for d in report.diagnostics:
                lines.append(
                    f"| `{d.severity}` | `{d.code}` | {d.layer} | `{d.path or ''}` | `{d.field or ''}` | {d.message} | `{d.recovery_action or ''}` |"
                )

        return "\n".join(lines)


def get_reporter(format_name: str) -> BaseReporter:
    name = format_name.lower().strip()
    if name == "json":
        return JSONReporter()
    elif name == "tap":
        return TAPReporter()
    elif name in ("markdown", "md"):
        return MarkdownReporter()
    else:
        return TerminalReporter()
