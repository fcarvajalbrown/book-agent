# AGENTS.md — LangGraph Concepts for This Project

## Coding Rules
- Comments: one line max, informal tone — no block comments, no docstrings
- No emojis anywhere (code, docs, commits)
- Commit messages: single short line
- Branding: `authors = ["Felipe Carvajal Brown"]` in Cargo.toml
- Fixes: root cause only — no test workarounds, no suppression

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
    errors: list[str]
    approved: bool
```

## Graph (graph.py)
Wires nodes together. Supports conditional edges (e.g. skip a node if no errors).

```python
from langgraph.graph import StateGraph
from state import BookState
from nodes.md_to_latex import md_to_latex
# ... other imports

builder = StateGraph(BookState)

builder.add_node("md_to_latex", md_to_latex)
builder.add_node("rasterize_svg", rasterize_svg)
# ... add all nodes

builder.set_entry_point("md_to_latex")
builder.add_edge("md_to_latex", "rasterize_svg")
builder.add_edge("rasterize_svg", "embed_images")
# ... chain all edges

graph = builder.compile()
```

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

To resume after interrupt:
```python
graph.invoke(None, config={"configurable": {"thread_id": "1"}})
```
Requires a checkpointer (e.g. `MemorySaver`) to persist state between interrupts.

## Checkpointer (required for interrupt)
```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

# Run with thread_id so state is saved
config = {"configurable": {"thread_id": "book-run-1"}}
graph.invoke(initial_state, config=config)
```

## Running the Graph
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
    "approved": False,
}

result = graph.invoke(initial_state, config=config)
```

## Key Packages
```
langgraph
langchain-core
langchain-openai   # or langchain-anthropic — swap freely, graph is agnostic
cairosvg           # SVG → PNG rasterization
```

## LLM Calls Inside Nodes
Nodes that need an LLM (e.g. md_to_latex, validate) use langchain-core:

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI  # swap for any provider

llm = ChatOpenAI(model="gpt-4o")  # or ChatAnthropic, etc.

def md_to_latex(state: BookState) -> BookState:
    prompt = ChatPromptTemplate.from_template("Convert this MD to LaTeX:\n{draft}")
    chain = prompt | llm
    result = chain.invoke({"draft": open(state["draft_path"]).read()})
    state["latex_content"] = result.content
    return state
```

## Debugging
```python
# Stream node-by-node output
for step in graph.stream(initial_state, config=config):
    print(step)
```
