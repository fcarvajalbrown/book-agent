from langgraph.types import interrupt

from state import BookState


def human_review(state: BookState) -> BookState:
    # pause graph and wait for human approval
    response = interrupt("Review the PDF and approve? (yes/no)")
    state["approved"] = response.strip().lower() == "yes"
    return state
