import os
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph
from langgraph.types import Send

MAX_CHUNK_CHARS = 10000

SYSTEM_PROMPT = (
    "Convert the provided markdown to a LaTeX fragment. "
    "Preserve all inline math $...$ and display math $$...$$ exactly. "
    "Convert markdown tables to tabular environments. "
    "Convert citations like (Author, Year) to \\cite{...} placeholders. "
    "Output ONLY the LaTeX body fragment. No preamble, no document environment."
)


def _check_conventions(text: str) -> list[str]:
    issues = []
    headings = re.findall(r"^(#{1,6})\s+(.+)$", text, flags=re.MULTILINE)
    if headings:
        levels = [len(h[0]) for h in headings]
        if len([lvl for lvl in levels if lvl == 1]) > 1:
            issues.append(f"multiple top-level (#) headings: {len([l for l in levels if l == 1])}")
        for i in range(1, len(levels)):
            if levels[i] > levels[i - 1] + 1:
                issues.append(
                    f"heading skip: {'#' * levels[i - 1]} -> {'#' * levels[i]}"
                )
    if re.search(r"\n{4,}", text):
        issues.append("excessive blank lines found (3+ consecutive newlines)")
    return issues


def _split_by_headings(text: str, level: int) -> list[str]:
    pattern = re.escape("#" * level)
    parts = re.split(rf"(?=^{pattern}\\s)", text, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def _split_chunk(text: str, level: int = 2) -> list[str]:
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]

    if level <= 3:
        parts = _split_by_headings(text, level)
        if len(parts) > 1:
            out = []
            for p in parts:
                out.extend(_split_chunk(p, level + 1))
            return out

    # paragraph split with budget
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paras) > 1:
        out, current = [], ""
        for p in paras:
            sep = "\n\n" if current else ""
            if len(current) + len(sep) + len(p) > MAX_CHUNK_CHARS and current:
                out.append(current)
                current = p
            else:
                current = current + sep + p
        if current:
            out.append(current)
        # recursively split any chunk that still exceeds the budget
        flat = []
        for chunk in out:
            if len(chunk) > MAX_CHUNK_CHARS:
                flat.extend(_split_chunk(chunk, level + 1))
            else:
                flat.append(chunk)
        if len(flat) > 1:
            return flat

    # hard split at line boundary
    out = []
    while text:
        if len(text) <= MAX_CHUNK_CHARS:
            out.append(text.strip())
            break
        split_at = text.rfind("\n", 0, MAX_CHUNK_CHARS)
        if split_at <= 0:
            split_at = MAX_CHUNK_CHARS
        out.append(text[:split_at].strip())
        text = text[split_at:].lstrip()
    return out


def load_and_split(state: dict[str, Any]) -> dict[str, Any]:
    path = state.get("draft_path", "")
    if not os.path.exists(path):
        return {
            "chunks": [],
            "errors": state.get("errors", []) + [f"draft not found: {path}"],
        }

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    errors = list(state.get("errors", []))
    errors.extend(_check_conventions(text))

    raw_chunks = _split_chunk(text, level=2)
    chunks = [{"index": i, "text": c} for i, c in enumerate(raw_chunks)]
    return {"chunks": chunks, "errors": errors}


def convert_chunk(state: dict[str, Any]) -> dict[str, Any]:
    chunk = state["chunk"]
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{markdown}"),
    ])
    from config import get_llm
    llm = get_llm()
    chain = prompt | llm
    response = chain.invoke({"markdown": chunk["text"]})
    return {"fragments": [{"index": chunk["index"], "latex": response.content}]}


def stitch(state: dict[str, Any]) -> dict[str, Any]:
    fragments = sorted(state.get("fragments", []), key=lambda x: x["index"])
    latex = "\n\n".join(f["latex"] for f in fragments)
    return {"latex_content": latex, "errors": state.get("errors", [])}


_sub_builder = StateGraph(dict)
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
