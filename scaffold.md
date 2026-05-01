book-agent/
├── draft/
│   ├── bhc_draft.md           # main manuscript
│   ├── bhc_glossary.md        # glossary
│   └── bhc_references.bib     # BibTeX references
├── assets/
│   ├── images/                # raster images (PNG/JPG, 300 PPI)
│   └── svg/                   # SVG diagrams (rasterized before LaTeX)
├── nodes/
│   ├── md_to_latex/           # sub-graph: split → parallel convert → stitch
│   │   ├── __init__.py
│   │   ├── splitter.py
│   │   └── sub_graph.py
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
│   ├── model_config.yaml      # LLM provider, model, base_url, api_key_env (gitignored)
│   ├── model_config_example.yaml  # template for model_config.yaml
│   ├── image_policy.yaml      # 300 PPI, sRGB, grayscale rules
│   └── run_config.yaml        # per-run: draft path, book size, color mode
├── outputs/
│   ├── manuscript.tex         # generated — gitignore
│   └── manuscript.pdf         # generated — gitignore
├── state.py                   # TypedDict shared agent state
├── graph.py                   # LangGraph node wiring
├── requirements.txt
└── README.md
