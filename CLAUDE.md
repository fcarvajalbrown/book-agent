# CLAUDE.md — Book Agent Project Context

## Goal
LangGraph agent pipeline that converts a Markdown book draft to a Lulu-compliant PDF.
Pipeline: MD → LaTeX → rasterize SVGs → embed images → apply Lulu template → compile PDF → validate → human review.

## Project Structure
```
book-agent/
├── draft/
│   ├── bhc_draft.md           # main manuscript
│   ├── bhc_glossary.md        # glossary
│   └── bhc_references.bib     # BibTeX references
├── assets/
│   ├── images/                # raster images (PNG/JPG, 300 PPI)
│   └── svg/                   # SVG diagrams (rasterized before LaTeX)
├── nodes/
│   ├── md_to_latex.py         # sub-graph: split → parallel convert → stitch
│   ├── rasterize_svg.py       # SVG → PNG at 300 PPI (pymupdf)
│   ├── embed_images.py        # resolve image paths, enforce policy
│   ├── apply_template.py      # inject Lulu geometry into .tex
│   ├── compile_pdf.py         # runs xelatex, captures errors
│   ├── validate_pdf.py        # checks fonts embedded, page size, no password
│   └── human_review.py        # interrupt() gate
├── prompts/
│   ├── math_rules.md          # inline vs display math conversion rules
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

`md_to_latex` is a sub-graph: reads the draft, checks heading and spacing conventions, then recursively splits by `##`, `###`, and paragraph breaks until every chunk is under `MAX_CHUNK_CHARS` (10000 chars). Fans out parallel LLM calls per chunk, then stitches results. Convention issues are appended to `errors` and forwarded through the sub-graph.

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
- Commit messages: single short line
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
- **Moonshot API key troubleshooting:** If every endpoint returns 401 even with a fresh key, check: (1) account verification status on platform.moonshot.cn, (2) IP allowlist restrictions, (3) console's built-in test button. The request format itself is correct.

## Status
All scaffold items implemented. Pipeline runs end-to-end via `run.py` with checkpoint resume.
