import subprocess
from pathlib import Path

from state import BookState

SVG_DIR = Path("assets/svg")
IMAGE_DIR = Path("assets/images")
DPI = 300


def _try_cairosvg(svg_path: Path, png_path: Path) -> None:
    import cairosvg
    with open(svg_path, "rb") as f:
        cairosvg.svg2png(file_obj=f, write_to=str(png_path), dpi=DPI)


def _try_inkscape(svg_path: Path, png_path: Path) -> None:
    subprocess.run(
        [
            "inkscape",
            str(svg_path),
            "--export-type=png",
            f"--export-filename={png_path}",
            f"--export-dpi={DPI}",
        ],
        check=True,
        capture_output=True,
    )


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
            _try_cairosvg(svg, png)
        except (OSError, ImportError) as cairo_err:
            try:
                _try_inkscape(svg, png)
            except (FileNotFoundError, subprocess.CalledProcessError) as ink_err:
                errors.append(
                    f"rasterize {svg.name}: cairo={cairo_err}; inkscape={ink_err}"
                )
                continue

        svg_map[str(svg)] = str(png)

    state["svg_map"] = svg_map
    state["errors"] = errors
    return state
