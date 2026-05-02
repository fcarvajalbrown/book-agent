import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nodes.validate_pdf import validate_pdf
from state import BookState


def test_missing_pdf():
    state: BookState = {
        "draft_path": "",
        "glossary_path": "",
        "references_path": "",
        "latex_content": "",
        "image_map": {},
        "svg_map": {},
        "pdf_path": "outputs/nonexistent.pdf",
        "errors": [],
        "approved": False,
    }
    result = validate_pdf(state)
    assert any("pdf not found" in e for e in result["errors"])
