from pathlib import Path

from pypdf import PdfReader

from state import BookState

# lulu 6x9 trim + 0.125in bleed
EXPECTED_WIDTH_PT = 6.25 * 72
EXPECTED_HEIGHT_PT = 9.25 * 72
TOLERANCE_PT = 2.0


def validate_pdf(state: BookState) -> BookState:
    pdf_path = state.get("pdf_path")
    errors = list(state.get("errors", []))

    if not pdf_path or not Path(pdf_path).exists():
        err = f"pdf not found: {pdf_path}"
        print(f"  [validate_pdf] ERROR: {err}")
        errors.append(err)
        state["errors"] = errors
        return state

    try:
        reader = PdfReader(pdf_path)
    except (OSError, ValueError) as exc:
        err = f"cannot read pdf: {exc}"
        print(f"  [validate_pdf] ERROR: {err}")
        errors.append(err)
        state["errors"] = errors
        return state

    print(f"  [validate_pdf] {pdf_path} — {len(reader.pages)} page(s)")

    if reader.is_encrypted:
        err = "pdf is password protected"
        print(f"  [validate_pdf] ERROR: {err}")
        errors.append(err)

    if len(reader.pages) == 0:
        err = "pdf has no pages"
        print(f"  [validate_pdf] ERROR: {err}")
        errors.append(err)

    for i, page in enumerate(reader.pages):
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        if abs(w - EXPECTED_WIDTH_PT) > TOLERANCE_PT or abs(h - EXPECTED_HEIGHT_PT) > TOLERANCE_PT:
            err = (
                f"page {i+1} size {w:.1f}x{h:.1f}pt does not match expected "
                f"{EXPECTED_WIDTH_PT:.1f}x{EXPECTED_HEIGHT_PT:.1f}pt"
            )
            print(f"  [validate_pdf] ERROR: {err}")
            errors.append(err)

        # basic font check: every page should reference at least one font in resources
        resources = page.get("/Resources", {})
        fonts = resources.get("/Font", {})
        if not fonts:
            err = f"page {i+1} has no embedded fonts"
            print(f"  [validate_pdf] ERROR: {err}")
            errors.append(err)

    state["errors"] = errors
    return state
