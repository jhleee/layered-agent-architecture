from typing import Annotated, TypedDict
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """에이전트 전역 상태."""
    messages: Annotated[list, add_messages]
    current_plan: str
    iteration: int
    final_answer: str | None
