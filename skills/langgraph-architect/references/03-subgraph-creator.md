# 03 — 서브그래프 추가

> 작업 전 `assets/architecture-rules.md`를 먼저 읽는다.

---

## 절차

### Step 1 — 서브그래프 파일 생성

`graphs/<subgraph_name>.py` 파일을 생성한다.

```python
# graphs/<name>.py
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END, add_messages
from core.models import reasoning_model  # Phase 2+


class <Name>State(TypedDict):
    """서브그래프 전용 부분 State."""
    messages: Annotated[list, add_messages]
    # 서브그래프 고유 필드 추가
    # 예: sources: list[str]
    # 예: draft: str


async def <step_1>(state: <Name>State) -> dict:
    """서브그래프 첫 번째 노드."""
    model = reasoning_model()
    response = await model.ainvoke(state["messages"])
    return {"messages": [response]}


async def <step_2>(state: <Name>State) -> dict:
    """서브그래프 두 번째 노드."""
    model = reasoning_model()
    response = await model.ainvoke(state["messages"])
    return {"messages": [response]}


def create_<name>_graph() -> StateGraph:
    """<name> 서브그래프를 생성한다."""
    builder = StateGraph(<Name>State)

    builder.add_node("<step_1>", <step_1>)
    builder.add_node("<step_2>", <step_2>)

    builder.add_edge(START, "<step_1>")
    builder.add_edge("<step_1>", "<step_2>")
    builder.add_edge("<step_2>", END)

    return builder.compile()
```

### Step 2 — 메인 그래프에 서브그래프 노드 등록

`graphs/main.py`에서 서브그래프를 노드로 등록한다.

```python
# graphs/main.py에 추가
from graphs.<name> import create_<name>_graph

# 서브그래프 인스턴스 생성
<name>_graph = create_<name>_graph()

# 노드로 등록
builder.add_node("<name>", <name>_graph)
```

### Step 3 — 라우팅 분기 추가

`nodes/routing.py`에 서브그래프 분기 조건을 추가한다.

```python
# nodes/routing.py에 서브그래프 라우팅 함수 추가

def select_subgraph(state: AgentState) -> str:
    """서브그래프 선택 라우팅 함수."""
    plan = state.get("current_plan", "")

    if "<조건 키워드>" in plan:
        return "<name>"
    # 다른 서브그래프 분기...
    else:
        return "direct"
```

`graphs/main.py`에 조건부 엣지 등록:

```python
builder.add_conditional_edges(
    "think",
    select_subgraph,
    {
        "<name>": "<name>",
        "direct": END,
    },
)
```

### Step 4 — 검증

- [ ] 서브그래프가 단독으로 `compile()` 가능한가
- [ ] 서브그래프 전용 State가 정의되어 있는가 (부분 State 권장)
- [ ] 서브그래프 간 직접 import가 없는가
- [ ] 메인 그래프에 노드로 등록되어 있는가
- [ ] 라우팅 함수에 분기 조건이 추가되어 있는가
- [ ] 의존성 방향 위반이 없는가

---

## 부분 State 패턴

서브그래프는 **부분 State**를 권장한다. 메인 `AgentState`와 독립적인 전용 State를 정의하여 서브그래프의 독립성을 유지한다.

| 전략 | 설명 | 적합한 경우 |
|------|------|-----------|
| **부분 State (권장)** | 서브그래프 전용 TypedDict 정의 | 서브그래프의 관심사가 독립적 |
| **전체 State 공유** | 메인 AgentState를 그대로 사용 | 서브그래프가 메인 State 대부분을 사용 |

### 예시: ResearcherState

```python
class ResearcherState(TypedDict):
    messages: Annotated[list, add_messages]
    sources: list[str]    # researcher 전용
    query: str            # researcher 전용
```

### 예시: WriterState

```python
class WriterState(TypedDict):
    messages: Annotated[list, add_messages]
    draft: str            # writer 전용
    topic: str            # writer 전용
```

---

## 서브그래프 간 통신

서브그래프끼리 **직접 통신하지 않는다**. 모든 데이터는 메인 그래프를 경유한다:

```
researcher 서브그래프
    → (결과를 메인 State에 기록)
         → 메인 그래프 라우팅
              → writer 서브그래프
                   ← (메인 State에서 researcher 결과 읽기)
```

---

## 규칙

- **서브그래프 1개 = 파일 1개**: `graphs/<name>.py`
- **팩토리 함수**: `create_<name>_graph()`로 생성
- **단독 테스트 가능**: 서브그래프만으로 compile + invoke 가능
- **직접 통신 금지**: 서브그래프 간 import 없음, 메인 그래프 경유
- **부분 State 권장**: 서브그래프 전용 TypedDict 정의
- **Phase 2 이상**: 서브그래프는 Phase 2부터 도입
