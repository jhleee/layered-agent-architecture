from core.state import AgentState


def should_continue(state: AgentState) -> str:
    """메인 그래프 라우팅: think 후 다음 행동을 결정한다.

    Returns:
        "execute_tools" — 도구 호출 필요
        "respond"       — 최종 답변
        "finalize"      — 최대 반복 도달 시 강제 종료
    """
    iteration = state.get("iteration", 0)
    if iteration >= 5:
        return "finalize"

    messages = state.get("messages", [])
    if not messages:
        return "respond"

    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tools"

    return "respond"
