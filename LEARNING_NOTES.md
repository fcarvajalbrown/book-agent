# Learning Notes — book-agent dev session

## Dependency Version Bumps

- Checked `langgraph>=0.2.0` to `>=1.1.9` and `langchain-core>=0.3.0` to `>=1.3.1`.
- Both versions exist on PyPI (latest 1.1.10 and 1.3.2 at time of check).
- Major 0.x to 1.x jumps signal breaking API changes. Verify nodes compile before committing.
- No lock file in repo — pins in `pyproject.toml` are the only constraints.

## Model Agnosticism

- Defaulted to `ChatOpenAI(model="gpt-4o-mini")` in `md_to_latex.py`. Wrong assumption.
- Felipe uses Moonshot/Kimi K2.6 via OpenAI-compatible endpoint.
- Refactored to `config/model_config.yaml` + `config/__init__.py:get_llm()` factory.
- Config is gitignored; `model_config_example.yaml` is committed as template.
- Provider, model, base_url, api_key_env all live in YAML. Nodes call `get_llm()`, know nothing about the provider.

## Config / Secrets Pattern

- Any file with secrets must be gitignored.
- Always commit an `_example` version so other users can copy and edit.
- Applies to: `model_config.yaml`, `.env`.

## Context Window and Chunking

- `bhc_draft.md` is 165KB. Single-level split on `##` is insufficient — sections can still exceed context limits.
- Recursive splitting: `##` -> `###` -> paragraph -> hard line break at `MAX_CHUNK_CHARS` (10K chars).
- Result: 36 chunks, max 8770 chars. Convention checker found 3 issues in draft (multiple h1s, heading skip, excessive blanks).

## Python Environment

- Created `.venv` locally with `python -m venv .venv`.
- `pip install -e .` creates `.egg-info/` in project root. Felipe refuses this.
- Use `pip install .` (non-editable). No egg folder.
- `.egg-info/` already in `.gitignore` as defense in depth.

## gitignore

- Hand-rolling `.gitignore` is error-prone. Use GitHub's official Python template.
- Must include: `.venv/`, `.env`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/`, build artifacts.
- Accidentally dropped `/assets` and `/draft` when rewriting — always verify after bulk replacement.

## Mermaid Diagrams

- GitHub renders Mermaid inline in markdown. No separate `.mmd` files needed.
- Place diagram directly in README.md under `## Architecture`.

## Badges

- shields.io for static badges. Simple icons via `?logo=` query param.
- Added: Python 3.11+, LangGraph 1.1+, MIT License.
- Need GitHub Actions workflow for dynamic badges (tests, build status).

## Tests

- Scaffolded `tests/` with `conftest.py` for fixtures, one test file per node.
- Tests must solve root problems, not just assert trivial passthroughs.
- `test_md_to_latex.py`: convention detection, recursive splitting, size bounds, order preservation.
- `test_embed_images.py`: SVG fallback by stem, missing image reporting, path replacement.
- `test_apply_template.py`: injection into template, missing template handling.
- `test_rasterize_svg.py`: cached PNG mapping (actual rasterization requires cairo binary).
- `test_compile_pdf.py`: missing tex error capture (actual xelatex requires TeX Live).
- `test_validate_pdf.py`: missing PDF handling (actual validation requires pypdf + real PDF).

## LangGraph Architecture

- No separate "AI observer." The compiled `StateGraph` IS the orchestrator.
- Nodes are plain Python functions: receive `BookState`, return updated `BookState`.
- Conditional edges (`should_rasterize`, `has_errors`) route flow.
- `MemorySaver` checkpointer persists state for `interrupt()` resume only.
- Observability options: LangSmith (native), custom logging wrapper on `graph.stream()`, or passthrough monitoring nodes.

## Node Implementation Order

1. `state.py` — TypedDict shared state
2. `graph.py` — StateGraph wiring with conditional edges
3. `config/__init__.py` — model-agnostic LLM factory
4. `nodes/md_to_latex.py` — sub-graph: convention check -> recursive split -> parallel LLM -> stitch
5. `nodes/rasterize_svg.py` — SVG to PNG at 300 DPI, cairo + inkscape fallback
6. `nodes/embed_images.py` — resolve `\includegraphics{...}` paths, SVG fallback by stem
7. `nodes/apply_template.py` — inject LaTeX into `templates/lulu_interior.tex`, write `outputs/manuscript.tex`
8. `nodes/compile_pdf.py` — xelatex two-pass, capture fatal errors
9. `nodes/validate_pdf.py` — pypdf checks: encryption, page size (6.25x9.25in), font presence
10. `nodes/human_review.py` — `interrupt()` gate

## Next Missing Pieces

- `templates/lulu_interior.tex` — Lulu geometry, font setup, body marker
- `prompts/math_rules.md` — inline vs display math conversion rules
- `prompts/style_guide.md` — voice rules (dense, no hedging, opinionated)
- `config/run_config.yaml` — per-run settings (draft path, book size, color mode)
- `config/image_policy.yaml` — 300 PPI, sRGB, grayscale rules
- GitHub Actions workflow for test/coverage badges
