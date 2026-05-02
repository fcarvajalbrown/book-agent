from pathlib import Path

from state import BookState

TEMPLATE_PATH = Path("templates/lulu_interior.tex")
BODY_MARKER = "% INSERT_BODY_HERE %"
OUTPUT_PATH = Path("outputs/manuscript.tex")


def apply_template(state: BookState) -> BookState:
    latex = state.get("latex_content", "")
    errors = list(state.get("errors", []))

    if not latex:
        errors.append("no latex content to inject")
        state["errors"] = errors
        return state

    if not TEMPLATE_PATH.exists():
        errors.append(f"template not found: {TEMPLATE_PATH}")
        state["errors"] = errors
        return state

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    if BODY_MARKER not in template:
        errors.append(f"template missing body marker: {BODY_MARKER}")
        state["errors"] = errors
        return state

    document = template.replace(BODY_MARKER, latex)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(document)

    state["pdf_path"] = str(OUTPUT_PATH.with_suffix(".pdf"))
    state["errors"] = errors
    return state
