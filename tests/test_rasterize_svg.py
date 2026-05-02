import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nodes.rasterize_svg import rasterize_svg
from state import BookState


def test_rasterize_maps_existing_pngs():
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
    result = rasterize_svg(state)
    assert result["errors"] == []
    if any(Path("assets/svg").glob("*.svg")):
        assert len(result["svg_map"]) > 0
    else:
        assert result["svg_map"] == {}
