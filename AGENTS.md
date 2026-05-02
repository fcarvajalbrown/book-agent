# AGENTS.md — LangGraph Concepts for This Project

## Coding Rules
- Comments: one line max, informal tone — no block comments, no docstrings
- No emojis anywhere (code, docs, commits)
- Commit messages: single short line
- Branding: `authors = ["Felipe Carvajal Brown"]` in Cargo.toml
- Fixes: root cause only — no test workarounds, no suppression

## Workflow Rules
- Work file by file in dependency order.
- After each file: give a one-line summary of what was done, then wait for an explicit "go" before writing the next file.
- **Commit and push before asking for the next go.** The user expects a clean checkpoint after every file.
- Do not batch-write multiple stubs in one turn.

## Lessons Learned for Future Agents
- Ask which LLM provider the user is using. Do not default to OpenAI.
- Install with `pip install .`, never `pip install -e .` — the user will not tolerate `.egg-info/` in the repo.
- Use the standard GitHub Python .gitignore template. Know it by heart or fetch it.
- Any file that may contain secrets must be gitignored, with an `_example` version committed in its place.
- Mermaid diagrams belong in README.md. Do not create separate `.mmd` files.
- The user is a senior developer who prefers root-cause fixes and dense, direct communication.
- Moonshot has two endpoints: `api.moonshot.cn` (mainland China) and `api.moonshot.ai` (international). A given key only works on one of them — keys minted from the international console return 401 on the `.cn` endpoint and vice versa. If a fresh key returns 401 everywhere, swap the base URL before chasing account-side issues.
- Moonshot model IDs use dots, not dashes (`kimi-k2.6`, not `kimi-k2-6`). The `kimi-k2.5`/`k2.6` reasoning models force `temperature: 1` and burn output budget on hidden reasoning tokens — for deterministic transformation tasks like MD→LaTeX, prefer `moonshot-v1-32k` or `moonshot-v1-128k`.

## Core Mental Model
Every node is a Python function: takes `state`, returns updated `state`.
LangGraph decides the order. That's it.

```python
def my_node(state: BookState) -> BookState:
    # do something
    state["latex_content"] = result
    return state
```

## State
Defined as a `TypedDict` in `state.py`. Shared across all nodes.
Think of it as the memory of the agent at any point in the pipeline.

```python
from typing import TypedDict, Optional

class BookState(TypedDict):
    draft_path: str           # draft/bhc_draft.md
    glossary_path: str        # draft/bhc_glossary.md
    references_path: str      # draft/bhc_references.bib
    latex_content: str
    image_map: dict           # {original_path: resolved_path}
    svg_map: dict             # {svg_path: rasterized_png_path}
    pdf_path: Optional[str]
    errors: list[str]        # fatal — routes graph to END
    warnings: list[str]      # non-fatal — surfaced but does not block compile
    approved: bool
```

## Graph (graph.py)
Wires nodes together. Supports conditional edges (skip rasterize if no SVGs, skip human review on validation errors).

```python
from langgraph.graph import StateGraph, END
from state import BookState
from nodes.md_to_latex import md_to_latex
# ... other imports

def should_rasterize(state: BookState) -> str:
    return "rasterize_svg" if state["svg_map"] else "embed_images"

def has_errors(state: BookState) -> str:
    return END if state.get("errors") else "human_review"

builder = StateGraph(BookState)
builder.add_node("md_to_latex", md_to_latex)
builder.add_node("rasterize_svg", rasterize_svg)
# ... add all nodes

builder.set_entry_point("md_to_latex")
builder.add_conditional_edges("md_to_latex", should_rasterize)
builder.add_edge("rasterize_svg", "embed_images")
# ... chain all edges
builder.add_conditional_edges("validate_pdf", has_errors)

graph = builder.compile(checkpointer=FileSaver())
```

## Checkpointer: FileSaver (persistent, not in-memory)
Custom checkpointer at `memory/__init__.py` — subclasses `InMemorySaver` and pickles state to `memory/checkpoints/state.pkl` after every write. On restart, previous state is loaded automatically so the pipeline resumes from the last completed node without re-burning LLM tokens.

```python
from memory import FileSaver

checkpointer = FileSaver()
graph = builder.compile(checkpointer=checkpointer)
```

`memory/checkpoints/` is gitignored.

## Conditional Edges
Run a node only if a condition is met.

```python
def should_rasterize(state: BookState) -> str:
    return "rasterize_svg" if state["svg_map"] else "embed_images"

builder.add_conditional_edges("md_to_latex", should_rasterize)
```

## Human-in-the-Loop (interrupt)
Pauses the graph and waits for your input before continuing.

```python
from langgraph.types import interrupt

def human_review(state: BookState) -> BookState:
    response = interrupt("Review the PDF and approve? (yes/no)")
    state["approved"] = response.strip().lower() == "yes"
    return state
```

`run.py` handles resume automatically: it detects the saved checkpoint, prompts for approval, and sends `Command(resume="yes")` to continue.

To resume programmatically:
```python
from langgraph.types import Command
graph.invoke(Command(resume="yes"), config={"configurable": {"thread_id": "1"}})
```

Requires a checkpointer to persist state between interrupts.

## Running the Graph
Use `run.py` which handles streaming, checkpoint resume, and human-in-the-loop:

```bash
python run.py
```

For programmatic use:
```python
initial_state: BookState = {
    "draft_path": "draft/bhc_draft.md",
    "glossary_path": "draft/bhc_glossary.md",
    "references_path": "draft/bhc_references.bib",
    "latex_content": "",
    "image_map": {},
    "svg_map": {},
    "pdf_path": None,
    "errors": [],
    "warnings": [],
    "approved": False,
}

result = graph.invoke(initial_state, config=config)
```

## Key Packages
```
langgraph
langchain-core
langchain-openai   # or langchain-anthropic — swap freely, graph is agnostic
pymupdf            # SVG → PNG rasterization, PDF validation
pyyaml             # config parsing
pytest             # testing
```

## LLM Calls Inside Nodes
Nodes that need an LLM (e.g. md_to_latex, validate) use `config.get_llm()`:

```python
from langchain_core.prompts import ChatPromptTemplate
from config import get_llm

llm = get_llm()  # reads config/model_config.yaml, returns any provider
```

Copy `config/model_config_example.yaml` to `config/model_config.yaml` (gitignored) and edit:

```yaml
provider: openai
model: moonshot-v1-32k
base_url: https://api.moonshot.ai/v1
api_key_env: MOONSHOT_API_KEY
temperature: 0.0
```

## Sub-graph: md_to_latex (parallel chunk conversion)
`md_to_latex` is a compiled sub-graph, not a single function. It:
1. `load_and_split` — reads draft, checks conventions, splits into chunks under `MAX_CHUNK_CHARS`
2. `convert_chunk` — each chunk gets its own LLM call via `Send()` (parallel)
3. `stitch` — joins fragments back in order

**Critical: the sub-graph state uses `Annotated` reducers.**
`fragments` is `Annotated[list[dict], operator.add]` so parallel `convert_chunk` writes are concatenated rather than overwriting each other. Without this, LangGraph throws `INVALID_CONCURRENT_GRAPH_UPDATE`.

The sub-graph state `SubState` extends `BookState` (TypedDict) so parent keys like `draft_path` are not stripped on entry.

```python
class SubState(BookState):
    chunks: list[dict]
    fragments: Annotated[list[dict], operator.add]
    chunk: dict
```

```python
from langgraph.types import Send

_sub_builder = StateGraph(SubState)
_sub_builder.add_node("load_and_split", load_and_split)
_sub_builder.add_node("convert_chunk", convert_chunk)
_sub_builder.add_node("stitch", stitch)
_sub_builder.set_entry_point("load_and_split")
_sub_builder.add_conditional_edges(
    "load_and_split",
    lambda s: [Send("convert_chunk", {"chunk": c}) for c in s.get("chunks", [])],
)
_sub_builder.add_edge("convert_chunk", "stitch")
md_to_latex = _sub_builder.compile()
```

## Checkpoint Recovery
If the pipeline crashes (rate limit, token exhaustion, network error), the checkpoint preserves state. Run again to resume from the last saved node — no work is lost.

## Debugging
```python
# Stream node-by-node output
for step in graph.stream(initial_state, config=config):
    print(step)
```

All nodes print `[nodename] ...` logs so failures are visible in real time.
