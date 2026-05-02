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

---

## Open Questions (with Answers)

### 1. What exactly does `MemorySaver` persist between `interrupt()` calls — the full state dict, or only diffs? Where is it stored on disk?
**Answer:** `MemorySaver` persists the full `BookState` dict (serialized via `pickle` or `json` depending on the checkpointer). It stores checkpoint tuples `(config, checkpoint, metadata)` in an in-memory dict by default. For disk persistence, swap `MemorySaver` for `SqliteSaver` or `PostgresSaver` from `langgraph.checkpoint.sqlite` / `langgraph.checkpoint.postgres`.

### 2. If a `convert_chunk` LLM call fails with a rate limit or timeout, does LangGraph retry the single chunk or the entire sub-graph? Where is retry logic configured?
**Answer:** LangGraph does not auto-retry failed nodes. Retry logic must be wrapped inside the node function (e.g., `tenacity.retry`) or configured on the LangChain model itself with `max_retries`. A failed chunk will propagate an exception that halts the entire graph unless caught inside the node. Use `try/except` in `convert_chunk` and append errors to `state["errors"]` for graceful degradation.

### 3. How does `get_llm()` handle model provider switches at runtime without reimporting? Is the import inside the function a performance concern for 36 parallel chunks?
**Answer:** The import is done once per process due to Python's module cache (`sys.modules`). Moving `from langchain_openai import ChatOpenAI` to module level is cleaner and has zero performance difference. The current inner import is defensive but unnecessary. For 36 parallel chunks, the bottleneck is HTTP latency, not import overhead.

### 4. The `pypdf` font check only verifies `/Font` resources exist in the page dictionary. Does this guarantee the font is embedded (subset or full), or just referenced? How to check for subset embedding vs. external font linking?
**Answer:** Checking `/Font` only verifies a reference exists, not embedding. To confirm embedding, iterate the font objects and check for `/FontDescriptor` with `/FontFile2` (TrueType) or `/FontFile3` (Type1/CFF). If these keys are absent, the font is referenced but not embedded. For subsetting, check if the font name contains a `+` prefix (e.g., `ABCDEF+TimesNewRoman`) which indicates subsetting by most PDF producers.

### 5. `cairosvg` requires system cairo libraries which fail on Windows without extra installation. Should the node prefer `inkscape` CLI on Windows and `cairosvg` on Linux/macOS, or is there a pure-Python SVG rasterizer?
**Answer:** The current implementation already tries cairosvg first, then falls back to inkscape. On Windows, inkscape is the practical choice. There is no widely-used pure-Python SVG rasterizer that produces print-quality output at 300 DPI. For CI/server environments without either, consider `resvg` (Rust binary, single executable, no system deps) as a third fallback.

### 6. If `md_to_latex` produces LaTeX with unicode characters that xelatex handles but pdflatex does not, how do we ensure the template uses `fontspec` and `xelatex` is explicitly enforced?
**Answer:** The template `templates/lulu_interior.tex` must include `\usepackage{fontspec}` and use Unicode-aware fonts (e.g., `\setmainfont{TeX Gyre Termes}`). The `compile_pdf` node already hardcodes `xelatex` as the compiler. If someone swaps to `pdflatex` in that node, compilation will fail on unicode. This is a documentation concern, not a code concern — the template and compiler must be kept in sync.

### 7. What happens to in-flight parallel `convert_chunk` calls if the `human_review` node rejects the output? Does LangGraph cancel pending tasks or let them finish?
**Answer:** LangGraph does not preempt or cancel in-flight tasks. By the time `human_review` runs, all upstream nodes (including all `convert_chunk` calls) have already completed. The `human_review` node is the final gate before `END`. If the user rejects, the graph ends with `approved=False`. There are no pending tasks to cancel at that stage. Preemption would require custom async task management outside LangGraph's scope.

### 8. The `validate_pdf` page size check hardcodes 6.25x9.25in. Should this be driven by `config/run_config.yaml` so the same pipeline can produce different book sizes without code changes?
**Answer:** Yes. The `BookState` should gain a `book_size` field (e.g., `"6x9"`) and `validate_pdf` should read dimensions from `config/run_config.yaml` or a lookup table. `apply_template` would also need to select the correct geometry. This is the right abstraction for multi-format publishing but is out of scope for the current single-book pipeline.

### 9. How does `graph.stream()` handle backpressure when `md_to_latex` fans out 36 parallel LLM calls? Is there a max concurrency setting, or does it spawn all at once?
**Answer:** LangGraph's `Send` mechanism dispatches all chunks concurrently by default. There is no built-in concurrency limiter. For API rate limits, throttle at the `get_llm()` level using `langchain_core.rate_limiters.InMemoryRateLimiter` or `tenacity` with `wait_exponential`. Alternatively, replace `Send` with a batched map-reduce pattern if the provider has strict concurrent request limits.

### 10. If the draft contains math that the LLM converts incorrectly (e.g., `$\nabla$` becomes plain text), what is the remediation path? Edit the prompt, add a post-processing node, or validate LaTeX with `latexindent`/`chktex` before compilation?
**Answer:** All three layers are useful: (1) Stronger prompts in `prompts/math_rules.md` reduce error rate, (2) A post-processing node using regex to re-wrap bare math symbols in `$...$` catches common patterns, (3) Running `chktex` or a `latex` dry-run before the full two-pass compilation surfaces syntax errors early. The cheapest fix is prompt engineering; the most robust is a validation node that fails fast on unclosed math environments.
