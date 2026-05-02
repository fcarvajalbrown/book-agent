from pathlib import Path

from pypdf import PdfReader

from state import BookState

# lulu 6x9 trim + 0.125in bleed
EXPECTED_WIDTH_PT = 6.25 * 72
EXPECTED_HEIGHT_PT = 9.25 * 72
TOLERANCE_PT = 2.0
MIN_PDF_VERSION = (1, 4)


def _font_is_embedded(font_obj) -> bool:
    # type0 fonts hold the descriptor on a descendant; look there first
    descendants = font_obj.get("/DescendantFonts")
    if descendants:
        for d in descendants:
            try:
                desc = d.get_object().get("/FontDescriptor")
                if desc and any(k in desc.get_object() for k in ("/FontFile", "/FontFile2", "/FontFile3")):
                    return True
            except (KeyError, AttributeError):
                continue
        return False
    desc = font_obj.get("/FontDescriptor")
    if not desc:
        return False
    d = desc.get_object()
    return any(k in d for k in ("/FontFile", "/FontFile2", "/FontFile3"))


def validate_pdf(state: BookState) -> BookState:
    pdf_path = state.get("pdf_path")
    errors = list(state.get("errors", []))
    warnings = list(state.get("warnings", []))

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

    # pdf version (lulu requires 1.4+)
    header = reader.pdf_header or ""
    try:
        ver = tuple(int(x) for x in header.replace("%PDF-", "").split("."))
        if ver < MIN_PDF_VERSION:
            err = f"pdf version {header} is below lulu minimum %PDF-1.4"
            print(f"  [validate_pdf] ERROR: {err}")
            errors.append(err)
    except ValueError:
        warnings.append(f"could not parse pdf version from header: {header!r}")

    if reader.is_encrypted:
        err = "pdf is password protected (lulu rejects encrypted pdfs)"
        print(f"  [validate_pdf] ERROR: {err}")
        errors.append(err)

    if len(reader.pages) == 0:
        err = "pdf has no pages"
        print(f"  [validate_pdf] ERROR: {err}")
        errors.append(err)

    # collect unique fonts across the document and check each is embedded once
    seen_fonts: dict[str, bool] = {}
    for page in reader.pages:
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        if abs(w - EXPECTED_WIDTH_PT) > TOLERANCE_PT or abs(h - EXPECTED_HEIGHT_PT) > TOLERANCE_PT:
            err = (
                f"page size {w:.1f}x{h:.1f}pt does not match expected "
                f"{EXPECTED_WIDTH_PT:.1f}x{EXPECTED_HEIGHT_PT:.1f}pt"
            )
            print(f"  [validate_pdf] ERROR: {err}")
            errors.append(err)
            break

        resources = page.get("/Resources", {})
        fonts = resources.get("/Font", {}) if resources else {}
        for fref in fonts.values():
            try:
                fobj = fref.get_object()
                base = str(fobj.get("/BaseFont", "?"))
                if base in seen_fonts:
                    continue
                seen_fonts[base] = _font_is_embedded(fobj)
            except (KeyError, AttributeError) as exc:
                warnings.append(f"could not inspect font: {exc}")

    not_embedded = [name for name, ok in seen_fonts.items() if not ok]
    if not_embedded:
        err = f"fonts not embedded (lulu rejects this): {sorted(not_embedded)}"
        print(f"  [validate_pdf] ERROR: {err}")
        errors.append(err)
    else:
        print(f"  [validate_pdf] all {len(seen_fonts)} fonts embedded")

    state["errors"] = errors
    state["warnings"] = warnings
    return state
