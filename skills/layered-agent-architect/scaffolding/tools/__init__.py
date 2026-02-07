from tools.search import search_tool

TOOL_REGISTRY: dict = {
    "search": search_tool,
}


def get_tools(names: list[str] | None = None) -> list:
    """이름 목록으로 도구를 조회한다. None이면 전체 반환."""
    if names is None:
        return list(TOOL_REGISTRY.values())
    return [TOOL_REGISTRY[n] for n in names]


def get_tool_descriptions() -> str:
    """등록된 도구 설명을 문자열로 반환한다."""
    return "\n".join(
        f"- {name}: {tool.description}"
        for name, tool in TOOL_REGISTRY.items()
    )
