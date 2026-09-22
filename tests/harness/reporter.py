"""
tests/harness/reporter.py
Backward compatibility alias module for tests/harness/reporters.py.
"""
from .reporters import (
    BaseReporter,
    TerminalReporter,
    JSONReporter,
    TAPReporter,
    MarkdownReporter,
    get_reporter,
)

__all__ = [
    "BaseReporter",
    "TerminalReporter",
    "JSONReporter",
    "TAPReporter",
    "MarkdownReporter",
    "get_reporter",
]
