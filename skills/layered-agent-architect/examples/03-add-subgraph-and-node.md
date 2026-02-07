# 예시 3: 서브그래프 + 노드 복합 시나리오

## 사용자 프롬프트

> "리서처 서브그래프 추가해줘"

## 기대 동작

1. `references/03-subgraph-creator.md` + `references/04-node-creator.md` 참조
2. 세 파일 수정/생성:

### 생성: `graphs/researcher.py`

```python
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END, add_messages
from core.models import reasoning_model
from tools import get_tools


class ResearcherState(TypedDict):
    messages: Annotated[list, add_messages]
    sources: list[str]
    query: str


async def research(state: ResearcherState) -> dict:
    model = reasoning_model()
    tools = get_tools(["search"])
    model_with_tools = model.bind_tools(tools)
    response = await model_with_tools.ainvoke(state["messages"])
    return {"messages": [response]}


async def summarize(state: ResearcherState) -> dict:
    model = reasoning_model()
    response = await model.ainvoke(state["messages"])
    return {"messages": [response]}


def create_researcher_graph():
    builder = StateGraph(ResearcherState)
    builder.add_node("research", research)
    builder.add_node("summarize", summarize)
    builder.add_edge(START, "research")
    builder.add_edge("research", "summarize")
    builder.add_edge("summarize", END)
    return builder.compile()
```

### 수정: `graphs/main.py` — 서브그래프 노드 등록

```python
from graphs.researcher import create_researcher_graph

researcher = create_researcher_graph()
builder.add_node("researcher", researcher)
```

### 수정: `nodes/routing.py` — 라우팅 분기 추가

```python
def select_subgraph(state: AgentState) -> str:
    plan = state.get("current_plan", "")
    if "검색" in plan or "조사" in plan or "research" in plan.lower():
        return "researcher"
    return "direct"
```

## 핵심 검증 항목

- [ ] 서브그래프가 단독 `compile()` 가능
- [ ] 부분 State (`ResearcherState`) 사용
- [ ] 메인 그래프에 노드로 등록
- [ ] 라우팅 분기 조건 추가
- [ ] Phase 2 이상인지 확인 (서브그래프는 Phase 2+)
