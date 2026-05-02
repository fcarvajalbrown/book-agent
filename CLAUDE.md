# CLAUDE.md — Book Agent Project Context

## Goal
LangGraph agent pipeline that converts a Markdown book draft to a Lulu-compliant PDF.
Pipeline: MD → LaTeX → rasterize SVGs → embed images → apply Lulu template → compile PDF → validate → human review.

## Project Structure
```
book-agent/
├── draft/
│   ├── bhc_draft.md           # main manuscript (~165KB)
│   ├── bhc_glossary.md        # glossary
│   └── bhc_references.bib     # BibTeX references
├── assets/
│   ├── images/                # raster images (fig1-1.png ... fig7-4.png)
│   └── svg/                   # SVG diagrams (auto-rasterized before LaTeX)
├── nodes/
│   ├── md_to_latex.py         # sub-graph: split → parallel convert → stitch
│   ├── rasterize_svg.py       # SVG → PNG at 300 PPI (pymupdf)
│   ├── embed_images.py        # resolve image paths, fuzzy matching, strip unknown
│   ├── apply_template.py      # inject Lulu geometry into .tex
│   ├── compile_pdf.py         # runs xelatex, captures errors
│   ├── validate_pdf.py        # checks fonts embedded, page size, no password
│   └── human_review.py        # interrupt() gate
├── memory/                    # persistent checkpointer module
│   └── __init__.py            # FileSaver — pickles checkpoints to disk
├── prompts/
│   ├── math_rules.md          # inline vs display math conversion rules
│   ├── structure_rules.md     # heading map, char escaping, figure [H] placement
│   └── style_guide.md         # voice rules: dense, no hedging, opinionated
├── templates/
│   └── lulu_interior.tex      # Lulu geometry + font setup
├── config/
│   ├── model_config.yaml      # LLM provider, model, base_url, api_key_env (gitignored)
│   ├── model_config_example.yaml  # template for model_config.yaml
│   ├── image_policy.yaml      # 300 PPI, sRGB, grayscale rules
│   └── run_config.yaml        # per-run: draft path, book size, color mode
├── outputs/
│   ├── manuscript.tex         # generated — gitignore
│   └── manuscript.pdf         # generated — gitignore
├── tests/
│   ├── conftest.py            # shared fixtures
│   ├── test_md_to_latex.py    # convention checks + chunk splitting
│   ├── test_embed_images.py   # image resolution + fuzzy matching
│   ├── test_apply_template.py
│   ├── test_compile_pdf.py
│   ├── test_rasterize_svg.py
│   ├── test_validate_pdf.py
│   ├── test_config.py         # model config loader
│   └── __init__.py
├── state.py                   # TypedDict shared agent state
├── graph.py                   # LangGraph node wiring
├── run.py                     # entry point with streaming + checkpoint resume
├── LEARNING_NOTES.md          # dev session Q&A and architecture notes
├── requirements.txt
└── README.md
```

## Node Execution Order
```
md_to_latex (sub-graph) → rasterize_svg → embed_images → apply_template → compile_pdf → validate_pdf → human_review
```

Conditional edges:
- After `md_to_latex`: skip `rasterize_svg` if `svg_map` is empty
- After `validate_pdf`: route to `END` if `errors` is non-empty, else `human_review`

## Lulu Constraints (already researched)
- Page size: trim + 0.125in bleed (e.g. 6×9 → 6.25×9.25in)
- Safety margin: 0.50in all sides; gutter min 0.20in inner edge
- Images: 300 PPI minimum, fonts embedded or outlined
- No transparency layers, no trim marks, no password protection
- Color: sRGB preferred; B&W images must be grayscale, gamma 2.2–2.4

## Book
Byzantine Hallucination Consensus manual.
Audience: senior devs 5y+ and math enthusiasts.
Style: Stripe blog + Dijkstra essay — dense, direct, opinionated. No hedging.

## Coding Rules
- Comments: one line max, informal tone — no block comments, no docstrings
- No emojis anywhere (code, docs, commits)
- Commit messages: **Conventional Commits**, single line, lowercase. Format: `<type>: <description>` where type is one of `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `build`, `style`, `perf`, `ci`. Examples: `fix: forward-slash image paths so xelatex finds them`, `feat: add figure-marker preprocessor`. Never noun-only summaries, never multi-line bodies unless explicitly requested.
- Branding: `authors = ["Felipe Carvajal Brown"]` in Cargo.toml
- Fixes: root cause only — no test workarounds, no suppression

## Workflow Rules
- Work file by file in dependency order.
- After each file: give a one-line summary of what was done, then wait for an explicit "go" before writing the next file.
- **Commit and push before asking for the next go.** Do not accumulate changes across multiple files without committing.
- Do not batch-write stubs. One node = one turn = one commit.

## Lessons Learned (read before acting)
- **Never assume the LLM provider.** Ask. Felipe uses Moonshot/Kimi K2.6, not OpenAI.
- **Never hardcode models.** Always route through `config/get_llm()`.
- **Use `pip install .` (non-editable), never `pip install -e .`.** Felipe refuses `.egg-info/` folders in the project root.
- **Use GitHub's official Python .gitignore.** Do not hand-roll minimal ones.
- **Secrets go in gitignored files with `_example` templates committed.** (`model_config.yaml`, `.env`)
- **Mermaid diagrams go in README.md, not separate files.** GitHub renders them inline.
- **Do not create folders or files without asking first** unless they are the single file currently being worked on.
- **Moonshot endpoints are not interchangeable:** `api.moonshot.cn` (mainland) and `api.moonshot.ai` (international) each only accept keys minted from their own console. A 401 across every route on a fresh key usually means wrong base URL — swap `.cn`↔`.ai` before chasing account-side issues.
- **Moonshot model IDs use dots, not dashes:** `kimi-k2.6`, not `kimi-k2-6`. The `kimi-k2.5`/`k2.6` reasoning models force `temperature: 1` and spend output tokens on hidden reasoning. For deterministic MD→LaTeX, use `moonshot-v1-32k` (or `-128k`) which honors `temperature: 0.0`.

## Recent Changes (last session)
1. **Fixed `INVALID_CONCURRENT_GRAPH_UPDATE`** — sub-graph `fragments` key now uses `Annotated[list[dict], operator.add]` reducer so parallel `convert_chunk` writes concatenate instead of colliding.
2. **Fixed sub-graph state inheritance** — `SubState` extends `BookState` (TypedDict) instead of `dict`, ensuring parent keys like `draft_path` are preserved when the sub-graph is entered.
3. **Added node logging** — every node prints `[nodename] message` so pipeline progress and errors are visible in real time, not just as a dumped error list at the end.
4. **Tightened prompt against invented figures** — system prompt now says "Only use image filenames that appear explicitly in the markdown; do not invent figures."
5. **Unknown images are stripped** — `embed_images` replaces unresolved `\includegraphics[...]{...}` with a LaTeX comment (`% image not found: ...`) so `xelatex` won't hard-fail on missing files. The error is still tracked in `state["errors"]`.
6. **Fuzzy image filename matching** — `_core_id()` strips `fig`/`figure` prefixes and non-alphanumeric chars, then matches. Handles `Figure_3_2a` → `fig3-2a.png`, `figure_1_1` → `fig1-1.png`, etc.
7. **Persistent checkpointer** — replaced in-memory `MemorySaver` with custom `FileSaver` that pickles checkpoints to `memory/checkpoints/state.pkl`. Pipeline resumes after crashes without re-burning LLM tokens. Folder is gitignored.

## Active Bug
None. The previous `list index out of range` crash was resolved by the sub-graph fixes (parallel `fragments` reducer + `SubState(BookState)`). End-to-end run now reaches `compile_pdf` cleanly. `run.py` now prints a real traceback on failure.

## Status
Pipeline converts draft to LaTeX and writes `outputs/manuscript.tex`. Checkpointer persists state. Current blocker is installing `xelatex` (MiKTeX on Windows: https://miktex.org/download). Once installed, `compile_pdf` → `validate_pdf` → `human_review` should run through.

## State Convention
- `errors`: fatal failures that should route the graph to `END` (compile failed, pdf missing, validation failed).
- `warnings`: non-fatal issues that should be surfaced but not block compile (markdown convention issues, stripped image refs). Routing in `has_errors` checks `errors` only.
