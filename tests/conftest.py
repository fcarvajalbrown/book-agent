import pytest


@pytest.fixture
def sample_markdown():
    return (
        "# Title\n\n"
        "Intro paragraph here.\n\n"
        "## Section A\n\n"
        "Some content.\n\n"
        "### Subsection A1\n\n"
        "More content.\n\n"
        "## Section B\n\n"
        "Final content.\n"
    )


@pytest.fixture
def bad_markdown():
    return (
        "# Title One\n\n"
        "Intro.\n\n"
        "# Title Two\n\n"
        "### Skipped level\n\n"
        "Content.\n\n\n\n"
        "After excessive blank lines.\n"
    )


@pytest.fixture
def oversized_markdown():
    # build a section larger than MAX_CHUNK_CHARS by repeating
    body = "word " * 3000
    return f"## Big Section\n\n{body}\n"
