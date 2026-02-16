"""End-to-end Word workflow test: open -> type -> save -> PDF.

On Windows with MS Word installed: runs the real tool functions.
On non-Windows: verifies graceful fallback to instruction strings.
"""
import os
import sys
import platform
import time
import pytest
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mcp_servers.screen_dispatch import (
    open_application,
    type_text,
    save_document_as_pdf,
)


@pytest.mark.skipif(not IS_WINDOWS, reason="Word automation requires Windows")
class TestWordWorkflowWindows:
    """Full Word workflow on Windows — requires MS Word installed."""

    def test_01_open_word(self):
        result = open_application("word")
        assert "open" in result.lower() or "blank" in result.lower()
        time.sleep(3)  # Extra settle time for Word to fully load

    def test_02_type_text(self):
        result = type_text(
            "Word",
            "Dear Sarah, thank you for the lovely Sunday dinner. "
            "Tommy's drawings made my whole week!",
        )
        assert "typed" in result.lower() or "done" in result.lower()

    def test_03_save_as_pdf(self):
        pdf_path = os.path.join(
            os.environ.get("USERPROFILE", ""), "Desktop", "TechBuddy_Test.pdf"
        )
        result = save_document_as_pdf(pdf_path)
        assert "saved" in result.lower() or "pdf" in result.lower()
        # Verify PDF exists and is non-trivial
        assert Path(pdf_path).exists(), f"PDF not found at {pdf_path}"
        assert Path(pdf_path).stat().st_size > 1000, "PDF is too small (< 1KB)"

    def test_04_cleanup(self):
        # Clean up test PDF
        pdf_path = Path(os.environ.get("USERPROFILE", "")) / "Desktop" / "TechBuddy_Test.pdf"
        if pdf_path.exists():
            pdf_path.unlink()
        # Close Word via win32com
        try:
            import win32com.client
            word = win32com.client.GetActiveObject("Word.Application")
            word.ActiveDocument.Close(SaveChanges=0)
            word.Quit()
        except Exception:
            pass


@pytest.mark.skipif(IS_WINDOWS, reason="Non-Windows fallback test")
class TestWordWorkflowNonWindows:
    """Verify graceful fallback on non-Windows."""

    def test_open_word_returns_instructions(self):
        result = open_application("word")
        assert "applications menu" in result.lower()

    def test_type_text_returns_instructions(self):
        result = type_text("Word", "Hello")
        assert "type" in result.lower()

    def test_save_pdf_returns_instructions(self):
        result = save_document_as_pdf("/tmp/test.pdf")
        assert "step" in result.lower() or "pdf" in result.lower()
