"""
tests/harness/link_integrity.py
Backward-compatibility alias module for tests/harness/hypergraph_validator.py.
"""
from .hypergraph_validator import (
    HypergraphValidator,
    LinkIntegrityValidator,
    WIKILINK_PATTERN,
)

__all__ = ["HypergraphValidator", "LinkIntegrityValidator", "WIKILINK_PATTERN"]
