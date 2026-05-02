import subprocess
from pathlib import Path

from state import BookState

OUTPUT_TEX = Path("outputs/manuscript.tex")
OUTPUT_DIR = Path("outputs")


def compile_pdf(state: BookState) -> BookState:
    errors = list(state.get("errors", []))

    if not OUTPUT_TEX.exists():
        err = f"tex file not found: {OUTPUT_TEX}"
        print(f"  [compile_pdf] ERROR: {err}")
        errors.append(err)
        state["errors"] = errors
        return state

    try:
        print(f"  [compile_pdf] running xelatex on {OUTPUT_TEX} ...")
        # two-pass for cross-references and toc
        for _ in range(2):
            result = subprocess.run(
                ["xelatex", "-interaction=nonstopmode", OUTPUT_TEX.name],
                cwd=str(OUTPUT_DIR),
                capture_output=True,
                text=True,
                check=False,
            )
    except FileNotFoundError:
        err = "xelatex not found — install texlive or miktex"
        print(f"  [compile_pdf] ERROR: {err}")
        errors.append(err)
        state["errors"] = errors
        return state

    if result.returncode != 0:
        # extract the last error line from stdout for context
        lines = result.stdout.splitlines()
        fatal = [l for l in lines if "!" in l]
        summary = fatal[-1] if fatal else result.stdout[-500:]
        err = f"xelatex failed: {summary}"
        print(f"  [compile_pdf] ERROR: {err}")
        errors.append(err)
    else:
        print("  [compile_pdf] xelatex finished successfully")

    pdf_path = OUTPUT_TEX.with_suffix(".pdf")
    state["pdf_path"] = str(pdf_path) if pdf_path.exists() else None
    state["errors"] = errors
    return state
