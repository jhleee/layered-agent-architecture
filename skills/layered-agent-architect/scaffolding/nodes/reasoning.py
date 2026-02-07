from core.state import AgentState
from core.models import reasoning_model
from prompts.templates import SYSTEM_PROMPT
from langchain_core.messages import SystemMessage
from tools import get_tools


async def think(state: AgentState) -> dict:
    """추론 노드: 현재 상황을 분석하고 다음 행동을 결정한다."""
    model = reasoning_model()
    model_with_tools = model.bind_tools(get_tools())

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"],
    ]
    response = await model_with_tools.ainvoke(messages)

    has_tool_calls = bool(response.tool_calls)
    plan = "도구 호출 후 결과 분석 필요" if has_tool_calls else "최종 답변 준비 완료"

    return {
        "messages": [response],
        "current_plan": plan,
        "iteration": state.get("iteration", 0) + 1,
    }
