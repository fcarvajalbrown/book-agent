import sys
from pathlib import Path

from langgraph.types import Command

from graph import graph


def _prompt_approval() -> str:
    print("\n" + "=" * 60)
    print("HUMAN REVIEW REQUIRED")
    print("=" * 60)
    print("Review outputs/manuscript.pdf and outputs/manuscript.tex")
    print("Then type 'yes' to approve or 'no' to reject.")
    while True:
        response = input("approve? (yes/no): ").strip().lower()
        if response in ("yes", "no"):
            return response
        print("invalid input. type 'yes' or 'no'.")


def main() -> None:
    cfg_path = Path("config/model_config.yaml")
    if not cfg_path.exists():
        print("ERROR: config/model_config.yaml not found.")
        print("Copy config/model_config_example.yaml and fill in your API key.")
        sys.exit(1)

    thread_id = "book-run-1"
    config = {"configurable": {"thread_id": thread_id}}

    # check if we are resuming from an interrupt
    state_snapshot = graph.get_state(config)
    if state_snapshot and state_snapshot.next:
        # graph is paused at an interrupt
        response = _prompt_approval()
        print(f"\nresuming with: {response}")
        stream_input = Command(resume=response)
    else:
        # fresh run
        stream_input = {
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
        print("=" * 60)
        print("book-agent pipeline starting")
        print("=" * 60)

    last_node = None
    try:
        for step in graph.stream(stream_input, config=config):
            for node_name, node_state in step.items():
                last_node = node_name
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
                    tex_path = (node_state.get("pdf_path") or "").replace(".pdf", ".tex")
                    print(f"    output tex: {tex_path}")

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

    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user.")
        sys.exit(130)

    # if we ended at human_review without resuming, the interrupt is active
    snapshot = graph.get_state(config)
    if snapshot and snapshot.next and last_node == "human_review":
        print("\n[!] Pipeline paused for human review.")
        print("    Run this script again to resume and provide approval.")
        sys.exit(0)

    print("\n" + "=" * 60)
    print("pipeline complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
