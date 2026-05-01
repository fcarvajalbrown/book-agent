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
│   ├── md_to_latex.py         # MD + math → LaTeX
│   ├── rasterize_svg.py       # SVG → PNG at 300 PPI (cairosvg or inkscape CLI)
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
│   ├── image_policy.yaml      # 300 PPI, sRGB, grayscale rules
│   └── run_config.yaml        # per-run: draft path, book size, color mode
├── outputs/
│   ├── manuscript.tex         # generated — gitignore
│   └── manuscript.pdf         # generated — gitignore
├── state.py                   # TypedDict shared agent state
├── graph.py                   # LangGraph node wiring
├── requirements.txt
└── README.md
```

## Node Execution Order
```
md_to_latex → rasterize_svg → embed_images → apply_template → compile_pdf → validate_pdf → human_review
```

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

## Next Steps (in order)
1. Write `state.py` — TypedDict with: draft_path, glossary_path, references_path, latex_content, image_map, svg_map, pdf_path, errors, approved
2. Write `graph.py` — wire nodes + conditional edges
3. Write each node one by one
4. Write `prompts/math_rules.md` and `prompts/style_guide.md`
5. Write `templates/lulu_interior.tex`
6. Write `config/run_config.yaml` and `config/image_policy.yaml`
