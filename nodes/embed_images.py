import re
from pathlib import Path

from state import BookState

ASSETS_DIR = Path("assets")
IMAGE_DIR = ASSETS_DIR / "images"


def _resolve_image(ref: str, _image_map: dict, svg_map: dict) -> str | None:
    # try direct path first
    candidates = [Path(ref), IMAGE_DIR / ref, ASSETS_DIR / ref]
    for p in candidates:
        if p.exists():
            return str(p)
    # fallback to svg_map if the ref points to an svg that was rasterized
    if ref in svg_map:
        return svg_map[ref]
    # strip extension and try matching against svg_map keys
    stem = Path(ref).stem
    for svg_path, png_path in svg_map.items():
        if Path(svg_path).stem == stem:
            return png_path
    return None


def embed_images(state: BookState) -> BookState:
    latex = state.get("latex_content", "")
    if not latex:
        print("  [embed_images] no latex content, skipping")
        return state

    svg_map = state.get("svg_map", {})
    image_map = dict(state.get("image_map", {}))
    errors = list(state.get("errors", []))

    # match \includegraphics[...]{path} or plain \includegraphics{path}
    pattern = re.compile(r"(\\includegraphics(?:\[.*?\])?\{)([^}]+)(\})")
    found = pattern.findall(latex)
    print(f"  [embed_images] found {len(found)} image reference(s)")

    def replacer(m: re.Match) -> str:
        prefix, ref, suffix = m.group(1), m.group(2), m.group(3)
        resolved = _resolve_image(ref, image_map, svg_map)
        if resolved is None:
            err = f"image not found: {ref}"
            print(f"  [embed_images] ERROR: {err} — stripped from latex")
            errors.append(err)
            return f"% {err}"
        image_map[ref] = resolved
        print(f"  [embed_images] resolved {ref} -> {resolved}")
        return f"{prefix}{resolved}{suffix}"

    new_latex = pattern.sub(replacer, latex)

    state["latex_content"] = new_latex
    state["image_map"] = image_map
    state["errors"] = errors
    return state
