from pathlib import Path

import pymupdf

from state import BookState

SVG_DIR = Path("assets/svg")
IMAGE_DIR = Path("assets/images")
DPI = 300


def rasterize_svg(state: BookState) -> BookState:
    if not SVG_DIR.exists():
        return state

    svg_paths = sorted(SVG_DIR.glob("*.svg"))
    if not svg_paths:
        return state

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    svg_map = dict(state.get("svg_map", {}))
    errors = list(state.get("errors", []))

    for svg in svg_paths:
        png = IMAGE_DIR / svg.with_suffix(".png").name
        if png.exists() and png.stat().st_mtime >= svg.stat().st_mtime:
            svg_map[str(svg)] = str(png)
            continue

        try:
            doc = pymupdf.open(str(svg))
            page = doc[0]
            pix = page.get_pixmap(dpi=DPI)
            pix.save(str(png))
            doc.close()
        except (RuntimeError, OSError) as exc:
            errors.append(f"rasterize {svg.name}: {exc}")
            continue

        svg_map[str(svg)] = str(png)

    state["svg_map"] = svg_map
    state["errors"] = errors
    return state
