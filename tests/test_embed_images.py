import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nodes.embed_images import embed_images, _resolve_image
from state import BookState


def test_resolve_image_finds_svg_map_fallback():
    svg_map = {"assets/svg/fig1.svg": "assets/images/fig1.png"}
    assert _resolve_image("fig1", {}, svg_map) == "assets/images/fig1.png"
    assert _resolve_image("fig1.svg", {}, svg_map) == "assets/images/fig1.png"


def test_resolve_image_returns_none_when_missing():
    assert _resolve_image("nonexistent.png", {}, {}) is None


def test_embed_images_replaces_paths_and_maps():
    state: BookState = {
        "draft_path": "",
        "glossary_path": "",
        "references_path": "",
        "latex_content": r"\includegraphics[width=0.5\textwidth]{fig1}",
        "image_map": {},
        "svg_map": {"assets/svg/fig1.svg": "assets/images/fig1.png"},
        "pdf_path": None,
        "errors": [],
        "approved": False,
    }
    result = embed_images(state)
    assert "assets/images/fig1.png" in result["latex_content"]
    assert result["image_map"]["fig1"] == "assets/images/fig1.png"
    assert result["errors"] == []


def test_embed_images_reports_missing():
    state: BookState = {
        "draft_path": "",
        "glossary_path": "",
        "references_path": "",
        "latex_content": r"\includegraphics{missing.png}",
        "image_map": {},
        "svg_map": {},
        "pdf_path": None,
        "errors": [],
        "approved": False,
    }
    result = embed_images(state)
    assert any("missing.png" in e for e in result["errors"])
