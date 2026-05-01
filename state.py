from typing import TypedDict, Optional


class BookState(TypedDict):
    draft_path: str
    glossary_path: str
    references_path: str
    latex_content: str
    image_map: dict
    svg_map: dict
    pdf_path: Optional[str]
    errors: list[str]
    approved: bool
