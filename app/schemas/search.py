from typing import TypedDict, List

class SearchState(TypedDict):
    query: str
    links: List[str]
    valid_links: List[str]

