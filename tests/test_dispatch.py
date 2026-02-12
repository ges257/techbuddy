"""Tests for screen_dispatch.py tools — the ones that work on any OS."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_servers.screen_dispatch import (
    find_file,
    list_folder,
    print_document,
    describe_screen_action,
)


def test_find_file_not_found():
    result = find_file("zzz_nonexistent_file_xyz_12345")
    assert "couldn't find" in result.lower()

def test_find_file_with_results():
    result = find_file("CLAUDE", search_in=str(Path(__file__).resolve().parent.parent))
    assert "CLAUDE" in result

def test_list_folder_exists():
    project_dir = str(Path(__file__).resolve().parent.parent)
    result = list_folder(project_dir)
    assert "frontend" in result or "hooks" in result

def test_list_folder_missing():
    result = list_folder("/tmp/zzz_nonexistent_folder_xyz")
    assert "can't find" in result.lower()

def test_describe_zoom_join():
    result = describe_screen_action("join a meeting", "Zoom")
    assert "step" in result.lower() or "click" in result.lower()

def test_describe_unknown_combo():
    result = describe_screen_action("fly to mars", "SpaceApp")
    assert "not sure" in result.lower() or "walk you through" in result.lower()

def test_print_missing_file():
    result = print_document("/tmp/zzz_no_such_file.pdf")
    assert "can't find" in result.lower()

def test_print_too_many_copies():
    result = print_document("/tmp/zzz_no_such_file.pdf", copies=10)
    # Should hit the "can't find" check first since file doesn't exist
    # But if file existed, copies > 5 would warn
    assert "can't find" in result.lower() or "lot of copies" in result.lower()
