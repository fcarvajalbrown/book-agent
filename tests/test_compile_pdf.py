import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nodes.compile_pdf import compile_pdf
from state import BookState


def test_missing_tex():
    state: BookState = {
        "draft_path": "",
        "glossary_path": "",
        "references_path": "",
        "latex_content": "",
        "image_map": {},
        "svg_map": {},
        "pdf_path": None,
        "errors": [],
        "approved": False,
    }
    result = compile_pdf(state)
    assert any("tex file not found" in e for e in result["errors"])
    assert result["pdf_path"] is None
