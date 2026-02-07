from langchain_core.tools import tool


@tool
def search_tool(query: str) -> str:
    """웹에서 정보를 검색한다.

    Args:
        query: 검색할 질의
    """
    # TODO: 실제 검색 API 연동
    return f"'{query}'에 대한 검색 결과입니다."
