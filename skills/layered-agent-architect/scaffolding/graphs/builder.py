from langgraph.graph import StateGraph
from core.state import AgentState


def create_base_graph() -> StateGraph:
    """기본 StateGraph 빌더를 생성한다."""
    return StateGraph(AgentState)


def compile_graph(builder: StateGraph, checkpointer=None):
    """그래프를 컴파일한다. 체크포인터 주입을 지원한다."""
    kwargs = {}
    if checkpointer is not None:
        kwargs["checkpointer"] = checkpointer
    return builder.compile(**kwargs)
