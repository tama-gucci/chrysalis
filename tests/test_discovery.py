"""Discovery must not open bytes or hydrate an implicitly selected collection."""
from pathlib import Path
import pytest
from tests.test_portable_core import vault
from helpers.discovery import discover_originals
from helpers.ingestion_contract import discover_mounted_filesystem_source


def test_metadata_discovery_does_not_read_original_bytes(vault, monkeypatch):
    original = vault / "Attachments/Originals"
    (original / "nested").mkdir()
    (original / "nested/spec.pdf").write_bytes(b"Synthetic original bytes")
    (original / "image.png").write_bytes(b"Synthetic image bytes")
    def forbidden(*args, **kwargs):
        raise AssertionError("Discovery opened content")
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    result = discover_originals(vault, locker_root=original, discovery_roots=["."], max_depth=2)
    assert len(result["files"]) == 2
    assert all(row["sha256"] is None and row["bytes_available"] is False for row in result["files"])
    envelope = discover_mounted_filesystem_source(vault, {"local_mount_path": str(original), "discovery_roots": ["."]}, source_alias="originals", page_size=1)
    assert envelope["discovery_status"] == "partial_listing" and envelope["pagination"]["next_page_token"] == "1"


def test_discovery_depth_and_root_errors_are_not_empty_success(vault):
    original = vault / "Attachments/Originals"
    (original / "nested").mkdir()
    (original / "nested/spec.txt").write_text("Synthetic content")
    result = discover_originals(vault, locker_root=original, max_depth=0)
    assert result["listing_truncated"]
    envelope = discover_mounted_filesystem_source(vault, {"local_mount_path": str(original), "max_discovery_depth": 0}, source_alias="originals", page_size=1)
    assert envelope["discovery_status"] == "partial_listing" and envelope["pagination"]["truncated"]
    missing = discover_originals(vault, locker_root=original / "missing")
    assert missing["collection_status"] == "unavailable"
    with pytest.raises(ValueError):
        discover_originals(vault, locker_root=original, discovery_roots=["../outside"])
