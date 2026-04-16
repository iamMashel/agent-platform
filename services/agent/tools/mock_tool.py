from langchain_core.tools import tool


@tool
def search_tool(query: str) -> str:
    """Mock search tool that simulates a web search engine lookup.

    Args:
        query: The search query string.

    Returns:
        A mock search result string.
    """
    return (
        f"[MOCK SEARCH RESULT for '{query}'] "
        "This is a placeholder result. In production, replace with a real search API."
    )
