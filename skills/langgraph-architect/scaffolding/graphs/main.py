from langgraph.graph import StateGraph, START, END
from core.state import AgentState
from nodes.reasoning import think
from nodes.execution import execute_tools
from nodes.routing import should_continue


def create_graph(checkpointer=None):
    """메인 에이전트 그래프를 생성한다."""
    builder = StateGraph(AgentState)

    # 노드 등록
    builder.add_node("think", think)
    builder.add_node("execute_tools", execute_tools)

    # 엣지 연결
    builder.add_edge(START, "think")
    builder.add_conditional_edges(
        "think",
        should_continue,
        {
            "execute_tools": "execute_tools",
            "respond": END,
            "finalize": END,
        },
    )
    builder.add_edge("execute_tools", "think")

    # 컴파일
    kwargs = {}
    if checkpointer is not None:
        kwargs["checkpointer"] = checkpointer
    return builder.compile(**kwargs)
