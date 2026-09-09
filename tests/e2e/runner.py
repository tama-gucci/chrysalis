#!/usr/bin/env python3
"""
Chrysalis E2E Test Runner
Provides an opaque-box test runner supporting 4-Tier test execution,
fine-grained filtering by Tier and Feature, multiple output formats
(Terminal, TAP, JSON), and baseline TDD execution modes.
"""

import sys
import os
import re
import json
import time
import argparse
import unittest
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure project root and tests directory are on python path
TESTS_E2E_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_E2E_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.e2e.test_tier1_features import TestTier1FeatureCoverage
from tests.e2e.test_tier2_boundaries import TestTier2BoundaryAndCornerCases
from tests.e2e.test_tier3_interactions import TestTier3CrossFeatureInteractions
from tests.e2e.test_tier4_scenarios import TestTier4RealWorldScenarios


class CustomTAPTestResult(unittest.TestResult):
    """Formats test results in Test Anything Protocol (TAP) version 13."""
    def __init__(self, stream=None, descriptions=None, verbosity=None, durations=None, **kwargs):
        super().__init__()
        self.stream = sys.stdout
        self.test_index = 0
        self.records: List[Dict[str, Any]] = []

    def startTest(self, test):
        super().startTest(test)
        self.test_index += 1

    def addSuccess(self, test):
        super().addSuccess(test)
        test_id = test.id()
        desc = test.shortDescription() or ""
        line = f"ok {self.test_index} - {test_id} {desc}".strip()
        self.stream.write(line + "\n")
        self.records.append({"index": self.test_index, "status": "ok", "id": test_id, "desc": desc})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        test_id = test.id()
        desc = test.shortDescription() or ""
        err_msg = str(err[1])
        line = f"not ok {self.test_index} - {test_id} {desc} # {err_msg}".strip()
        self.stream.write(line + "\n")
        self.records.append({"index": self.test_index, "status": "not ok", "id": test_id, "error": err_msg})

    def addError(self, test, err):
        super().addError(test, err)
        test_id = test.id()
        desc = test.shortDescription() or ""
        err_msg = str(err[1])
        line = f"not ok {self.test_index} - {test_id} {desc} (ERROR) # {err_msg}".strip()
        self.stream.write(line + "\n")
        self.records.append({"index": self.test_index, "status": "error", "id": test_id, "error": err_msg})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        test_id = test.id()
        line = f"ok {self.test_index} - {test_id} # SKIP {reason}".strip()
        self.stream.write(line + "\n")
        self.records.append({"index": self.test_index, "status": "skip", "id": test_id, "reason": reason})


def collect_test_cases(tier: Optional[int] = None, feature: Optional[str] = None) -> unittest.TestSuite:
    """Builds test suite based on tier and feature filters."""
    suite = unittest.TestSuite()
    tier_classes = {
        1: [TestTier1FeatureCoverage],
        2: [TestTier2BoundaryAndCornerCases],
        3: [TestTier3CrossFeatureInteractions],
        4: [TestTier4RealWorldScenarios],
    }

    selected_classes = []
    if tier is not None:
        selected_classes.extend(tier_classes.get(tier, []))
    else:
        for c_list in tier_classes.values():
            selected_classes.extend(c_list)

    feature_norm = feature.upper() if feature else None

    for cls in selected_classes:
        loader = unittest.TestLoader()
        for name in loader.getTestCaseNames(cls):
            if feature_norm:
                # E.g. test_f1_*, test_f2_*, test_f3_*
                feat_tag = f"test_{feature_norm.lower()}_"
                if not name.lower().startswith(feat_tag) and feature_norm not in name.upper():
                    continue
            suite.addTest(cls(name))

    return suite


def main():
    parser = argparse.ArgumentParser(description="Chrysalis E2E Test Runner")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], help="Execute only tests from specified Tier (1-4)")
    parser.add_argument("--feature", type=str, help="Execute only tests for specified Feature (e.g. F1, F2, ..., F9)")
    parser.add_argument("--format", choices=["terminal", "tap", "json"], default="terminal", help="Output format")
    parser.add_argument("--allow-failures", action="store_true", help="Exit with 0 even if test failures exist (for baseline TDD reporting)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    suite = collect_test_cases(tier=args.tier, feature=args.feature)
    total_tests = suite.countTestCases()

    if total_tests == 0:
        print("No tests matched the specified filter criteria.")
        sys.exit(0)

    start_time = time.time()

    if args.format == "tap":
        sys.stdout.write(f"TAP version 13\n1..{total_tests}\n")
        runner = unittest.TextTestRunner(resultclass=CustomTAPTestResult, stream=open(os.devnull, 'w'), verbosity=0)
        result = runner.run(suite)
        duration = time.time() - start_time
    elif args.format == "json":
        # Run silently and collect structured data
        runner = unittest.TextTestRunner(stream=open(os.devnull, 'w'), verbosity=0)
        result = runner.run(suite)
        duration = time.time() - start_time
        
        failures_list = [{"test": test.id(), "error": err} for test, err in result.failures]
        errors_list = [{"test": test.id(), "error": err} for test, err in result.errors]
        
        report = {
            "summary": {
                "total": total_tests,
                "passed": total_tests - len(result.failures) - len(result.errors) - len(result.skipped),
                "failed": len(result.failures),
                "errors": len(result.errors),
                "skipped": len(result.skipped),
                "duration_seconds": round(duration, 3)
            },
            "failures": failures_list,
            "errors": errors_list
        }
        print(json.dumps(report, indent=2))
    else: # Terminal format
        print("=" * 72)
        print("CHRYSALIS E2E OPAQUE-BOX TEST RUNNER")
        print("=" * 72)
        print(f"Filter: Tier={args.tier or 'All (1-4)'} | Feature={args.feature or 'All (F1-F9)'}")
        print(f"Discovered: {total_tests} total tests")
        print("-" * 72)

        verbosity = 2 if args.verbose else 1
        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)
        duration = time.time() - start_time

        print("-" * 72)
        passed = total_tests - len(result.failures) - len(result.errors) - len(result.skipped)
        print(f"Summary: {passed} passed, {len(result.failures)} failed, {len(result.errors)} errors, {len(result.skipped)} skipped in {duration:.2f}s")
        print("=" * 72)

    if not args.allow_failures and (result.failures or result.errors):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
