from langgraph.prebuilt import ToolNode
from core.state import AgentState
from tools import get_tools

# 방법 1: ToolNode 활용 (단순)
tool_node = ToolNode(tools=get_tools())


# 방법 2: 커스텀 실행 (컨텍스트 누적 필요 시)
async def execute_tools(state: AgentState) -> dict:
    """도구 실행 노드: 추론 노드가 요청한 도구를 실행한다."""
    result = await tool_node.ainvoke(state)
    return {"messages": result.get("messages", [])}
