import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nodes.apply_template import apply_template
from state import BookState


def test_injects_latex_and_writes_file(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # mock template path inside temp dir
        tpl = tmp_path / "templates" / "lulu_interior.tex"
        tpl.parent.mkdir(parents=True, exist_ok=True)
        tpl.write_text(
            "\\documentclass{book}\n% INSERT_BODY_HERE %\n\\end{document}",
            encoding="utf-8",
        )

        out = tmp_path / "outputs" / "manuscript.tex"

        monkeypatch.setattr("nodes.apply_template.TEMPLATE_PATH", tpl)
        monkeypatch.setattr("nodes.apply_template.OUTPUT_PATH", out)

        state: BookState = {
            "draft_path": "",
            "glossary_path": "",
            "references_path": "",
            "latex_content": "\\section{Hello}",
            "image_map": {},
            "svg_map": {},
            "pdf_path": None,
            "errors": [],
            "approved": False,
        }
        result = apply_template(state)

        assert result["errors"] == []
        assert result["pdf_path"] == str(out.with_suffix(".pdf"))
        written = out.read_text(encoding="utf-8")
        assert "\\section{Hello}" in written
        assert "\\documentclass{book}" in written


def test_missing_template(monkeypatch):
    fake_tpl = Path("/nonexistent/templates/lulu_interior.tex")
    monkeypatch.setattr("nodes.apply_template.TEMPLATE_PATH", fake_tpl)

    state: BookState = {
        "draft_path": "",
        "glossary_path": "",
        "references_path": "",
        "latex_content": "\\section{Hello}",
        "image_map": {},
        "svg_map": {},
        "pdf_path": None,
        "errors": [],
        "approved": False,
    }
    result = apply_template(state)
    assert any("template not found" in e for e in result["errors"])
