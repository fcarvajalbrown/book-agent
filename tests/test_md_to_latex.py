import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nodes.md_to_latex import _check_conventions, _split_chunk, MAX_CHUNK_CHARS


def test_conventions_clean(sample_markdown):
    assert _check_conventions(sample_markdown) == []


def test_conventions_multiple_h1(bad_markdown):
    issues = _check_conventions(bad_markdown)
    assert any("multiple top-level" in i for i in issues)


def test_conventions_heading_skip(bad_markdown):
    issues = _check_conventions(bad_markdown)
    assert any("heading skip" in i for i in issues)


def test_conventions_excessive_blanks(bad_markdown):
    issues = _check_conventions(bad_markdown)
    assert any("excessive blank lines" in i for i in issues)


def test_split_small_chunk(sample_markdown):
    chunks = _split_chunk(sample_markdown)
    assert len(chunks) == 1
    assert "# Title" in chunks[0]


def test_split_oversized(oversized_markdown):
    chunks = _split_chunk(oversized_markdown)
    assert len(chunks) > 1
    assert all(len(c) <= MAX_CHUNK_CHARS for c in chunks)


def test_split_preserves_order(oversized_markdown):
    chunks = _split_chunk(oversized_markdown)
    combined = "\n\n".join(chunks)
    assert "## Big Section" in combined
    assert "word" in combined
