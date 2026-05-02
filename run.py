import sys
from pathlib import Path

from state import BookState
from graph import graph


def main() -> None:
    cfg_path = Path("config/model_config.yaml")
    if not cfg_path.exists():
        print("ERROR: config/model_config.yaml not found.")
        print("Copy config/model_config_example.yaml and fill in your API key.")
        sys.exit(1)

    initial_state: BookState = {
        "draft_path": "draft/bhc_draft.md",
        "glossary_path": "draft/bhc_glossary.md",
        "references_path": "draft/bhc_references.bib",
        "latex_content": "",
        "image_map": {},
        "svg_map": {},
        "pdf_path": None,
        "errors": [],
        "approved": False,
    }

    config = {"configurable": {"thread_id": "book-run-1"}}

    print("=" * 60)
    print("book-agent pipeline starting")
    print("=" * 60)

    try:
        for step in graph.stream(initial_state, config=config):
            for node_name, node_state in step.items():
                print(f"\n>>> NODE: {node_name}")

                if node_name == "load_and_split":
                    print(f"    chunks: {len(node_state.get('chunks', []))}")
                    errs = node_state.get("errors", [])
                    if errs:
                        print(f"    convention issues: {errs}")

                elif node_name == "convert_chunk":
                    frags = node_state.get("fragments", [])
                    for f in frags:
                        print(f"    chunk {f['index']} converted ({len(f['latex'])} chars)")

                elif node_name == "stitch":
                    print(f"    total latex: {len(node_state.get('latex_content', ''))} chars")

                elif node_name == "rasterize_svg":
                    print(f"    svg_map entries: {len(node_state.get('svg_map', {}))}")

                elif node_name == "embed_images":
                    print(f"    image_map entries: {len(node_state.get('image_map', {}))}")

                elif node_name == "apply_template":
                    print(f"    output tex: {node_state.get('pdf_path', '').replace('.pdf', '.tex')}")

                elif node_name == "compile_pdf":
                    print(f"    pdf_path: {node_state.get('pdf_path')}")
                    errs = node_state.get("errors", [])
                    if errs:
                        print(f"    errors: {errs[-1]}")

                elif node_name == "validate_pdf":
                    errs = node_state.get("errors", [])
                    if errs:
                        print(f"    validation errors: {errs}")
                    else:
                        print("    validation passed")

                elif node_name == "human_review":
                    print(f"    approved: {node_state.get('approved')}")
                    if not node_state.get("approved"):
                        print("\n[!] Pipeline paused for human review.")
                        print("    Type 'yes' to approve, 'no' to reject.")
                        print("    (Resume support: run again with same thread_id)")

    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user.")
        sys.exit(130)

    print("\n" + "=" * 60)
    print("pipeline complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
