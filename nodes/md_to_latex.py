import os
import re
from pathlib import Path
import operator
from typing import Any, Annotated

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph
from langgraph.types import Send

from state import BookState

MAX_CHUNK_CHARS = 10000
PROMPTS_DIR = Path("prompts")


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


MATH_RULES = _load_prompt("math_rules.md")
STYLE_GUIDE = _load_prompt("style_guide.md")

SYSTEM_PROMPT = (
    "Convert the provided markdown to a LaTeX fragment. "
    "Preserve all inline math $...$ and display math $$...$$ exactly. "
    "Convert markdown tables to tabular environments. "
    "Convert citations like (Author, Year) to \\cite{...} placeholders. "
    "Output ONLY the LaTeX body fragment. No preamble, no document environment.\n\n"
    + (MATH_RULES + "\n\n" if MATH_RULES else "")
    + (STYLE_GUIDE if STYLE_GUIDE else "")
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
    parts = re.split(rf"(?=^{pattern}\s)", text, flags=re.MULTILINE)
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
        flat = []
        for chunk in out:
            if len(chunk) > MAX_CHUNK_CHARS:
                flat.extend(_split_chunk(chunk, level + 1))
            else:
                flat.append(chunk)
        if len(flat) > 1:
            return flat

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
        err = f"draft not found: {path}"
        print(f"  [md_to_latex] {err}")
        return {
            "chunks": [],
            "errors": state.get("errors", []) + [err],
        }

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    errors = list(state.get("errors", []))
    issues = _check_conventions(text)
    if issues:
        for issue in issues:
            print(f"  [md_to_latex] convention issue: {issue}")
        errors.extend(issues)

    raw_chunks = _split_chunk(text, level=2)
    chunks = [{"index": i, "text": c} for i, c in enumerate(raw_chunks)]
    print(f"  [md_to_latex] split draft into {len(chunks)} chunk(s)")
    return {"chunks": chunks, "errors": errors}


def convert_chunk(state: dict[str, Any]) -> dict[str, Any]:
    chunk = state["chunk"]
    print(f"  [md_to_latex] converting chunk {chunk['index']} ({len(chunk['text'])} chars)")
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=chunk["text"]),
    ]
    from config import get_llm
    llm = get_llm()
    response = llm.invoke(messages)
    print(f"  [md_to_latex] chunk {chunk['index']} done ({len(response.content)} chars latex)")
    return {"fragments": [{"index": chunk["index"], "latex": response.content}]}


class SubState(BookState):
    chunks: list[dict]
    fragments: Annotated[list[dict], operator.add]
    chunk: dict


def stitch(state: SubState) -> dict[str, Any]:
    fragments = sorted(state.get("fragments", []), key=lambda x: x["index"])
    latex = "\n\n".join(f["latex"] for f in fragments)
    print(f"  [md_to_latex] stitched {len(fragments)} fragment(s) into {len(latex)} chars of latex")
    return {"latex_content": latex, "errors": state.get("errors", [])}


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
