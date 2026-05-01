from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from state import BookState
from nodes.md_to_latex import md_to_latex
from nodes.rasterize_svg import rasterize_svg
from nodes.embed_images import embed_images
from nodes.apply_template import apply_template
from nodes.compile_pdf import compile_pdf
from nodes.validate_pdf import validate_pdf
from nodes.human_review import human_review


def should_rasterize(state: BookState) -> str:
    return "rasterize_svg" if state["svg_map"] else "embed_images"


def has_errors(state: BookState) -> str:
    return END if state["errors"] else "human_review"


builder = StateGraph(BookState)

builder.add_node("md_to_latex", md_to_latex)
builder.add_node("rasterize_svg", rasterize_svg)
builder.add_node("embed_images", embed_images)
builder.add_node("apply_template", apply_template)
builder.add_node("compile_pdf", compile_pdf)
builder.add_node("validate_pdf", validate_pdf)
builder.add_node("human_review", human_review)

builder.set_entry_point("md_to_latex")
builder.add_conditional_edges("md_to_latex", should_rasterize)
builder.add_edge("rasterize_svg", "embed_images")
builder.add_edge("embed_images", "apply_template")
builder.add_edge("apply_template", "compile_pdf")
builder.add_edge("compile_pdf", "validate_pdf")
builder.add_conditional_edges("validate_pdf", has_errors)
builder.add_edge("human_review", END)

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)
