# 제9장 Graphs 레이어

> [← 이전: 제8장 Nodes 레이어](./08-nodes-레이어.md) | [목차](./index.md) | [다음: 제10장 Interfaces 레이어 →](./10-interfaces-레이어.md)

---

## 이 장의 파일 범위

```
graphs/
├── __init__.py
├── builder.py       ← 9.1
├── researcher.py    ← 9.2
├── writer.py        ← 9.2
└── main.py          ← 9.3
```

`graphs/` 레이어는 **노드를 연결하여 실행 흐름을 정의**하는 책임을 담당한다. `nodes/` 레이어가 "각 처리 단위가 무엇을 하는가"를 정의했다면, `graphs/` 레이어는 "그 단위들이 어떤 순서로, 어떤 조건에 따라 실행되는가"를 정의한다.

---

## 9.1 그래프 빌더 유틸리티 (builder.py)

### 9.1.1 설계 의도

그래프 조립 코드에는 반복되는 패턴이 존재한다:
- `StateGraph` 인스턴스 생성
- 노드 등록
- 엣지 연결
- 체크포인터 주입 후 컴파일

이 패턴을 `builder.py`에서 유틸리티 함수로 추상화하여 **그래프 조립 시 보일러플레이트를 줄인다**. 엔터프라이즈 접근의 Builder 패턴을 경량화한 것이다.

### 9.1.2 코드

```python
# graphs/builder.py

from langgraph.graph import StateGraph, START, END
from core.state import AgentState


def create_base_graph(state_class=AgentState) -> StateGraph:
    """기본 StateGraph 인스턴스를 생성한다.

    Args:
        state_class: 그래프에서 사용할 State 클래스

    Returns:
        설정된 StateGraph 인스턴스
    """
    return StateGraph(state_class)


def compile_graph(
    builder: StateGraph,
    checkpointer=None,
    store=None,
):
    """그래프를 컴파일한다.

    체크포인터와 저장소가 제공되면 주입한다.

    Args:
        builder: 노드와 엣지가 등록된 StateGraph
        checkpointer: 상태 영속화 체크포인터 (선택)
        store: 장기 메모리 저장소 (선택)
    """
    kwargs = {}
    if checkpointer is not None:
        kwargs["checkpointer"] = checkpointer
    if store is not None:
        kwargs["store"] = store

    return builder.compile(**kwargs)


def add_loop_with_routing(
    builder: StateGraph,
    think_node: str,
    route_func,
    route_map: dict[str, str],
):
    """추론→라우팅→실행 루프를 그래프에 추가하는 헬퍼.

    가장 흔한 에이전트 패턴인 think-route-act 루프를
    한 번의 함수 호출로 설정할 수 있다.

    Args:
        builder: StateGraph 인스턴스
        think_node: 추론 노드 이름
        route_func: 라우팅 함수
        route_map: 라우팅 결과 → 노드 이름 매핑
    """
    builder.add_conditional_edges(
        think_node,
        route_func,
        route_map,
    )
```

### 9.1.3 빌더 활용 예시

```python
# 빌더 없이 (반복적)
graph = StateGraph(AgentState)
graph.add_node("think", think)
graph.add_node("execute_tools", execute_tools)
graph.add_edge(START, "think")
graph.add_conditional_edges("think", should_continue, {...})
compiled = graph.compile(checkpointer=get_checkpointer())

# 빌더 활용 (간결)
graph = create_base_graph()
graph.add_node("think", think)
graph.add_node("execute_tools", execute_tools)
graph.add_edge(START, "think")
add_loop_with_routing(graph, "think", should_continue, {...})
compiled = compile_graph(graph, checkpointer=get_checkpointer())
```

빌더의 가치는 단순한 그래프에서는 미미하지만, 서브그래프가 여러 개이고 패턴이 반복될수록 커진다.

---

## 9.2 서브그래프 설계 패턴

### 9.2.1 서브그래프 = 독립 파일 원칙

[제2장 설계 원칙](./02-설계-원칙.md)의 원칙 7에 따라, 각 서브그래프는 **독립 파일**에 정의되며 **단독 테스트**가 가능해야 한다.

### 9.2.2 서브그래프 구현 예시

**리서처 서브그래프:**

```python
# graphs/researcher.py

from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END, add_messages
from core.models import reasoning_model
from tools import get_tools


class ResearcherState(TypedDict):
    """리서처 서브그래프 전용 State"""
    messages: Annotated[list, add_messages]
    sources: list[str]
    query: str


async def research(state: ResearcherState) -> dict:
    """리서치 수행 노드"""
    model = reasoning_model()
    tools = get_tools(["search"])
    model_with_tools = model.bind_tools(tools)

    response = await model_with_tools.ainvoke(state["messages"])
    return {"messages": [response]}


async def summarize(state: ResearcherState) -> dict:
    """리서치 결과 요약 노드"""
    model = reasoning_model()
    summary_prompt = "지금까지의 리서치 결과를 요약해주세요."
    response = await model.ainvoke(
        state["messages"] + [{"role": "user", "content": summary_prompt}]
    )
    return {"messages": [response]}


def create_researcher_graph() -> StateGraph:
    """리서처 서브그래프를 생성한다."""
    builder = StateGraph(ResearcherState)

    builder.add_node("research", research)
    builder.add_node("summarize", summarize)

    builder.add_edge(START, "research")
    builder.add_edge("research", "summarize")
    builder.add_edge("summarize", END)

    return builder.compile()
```

**라이터 서브그래프:**

```python
# graphs/writer.py

from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END, add_messages
from core.models import creative_model


class WriterState(TypedDict):
    """라이터 서브그래프 전용 State"""
    messages: Annotated[list, add_messages]
    draft: str
    topic: str


async def write_draft(state: WriterState) -> dict:
    """초안 작성 노드"""
    model = creative_model()
    response = await model.ainvoke(state["messages"])
    return {
        "messages": [response],
        "draft": response.content,
    }


async def refine(state: WriterState) -> dict:
    """초안 다듬기 노드"""
    model = creative_model()
    refine_prompt = f"다음 초안을 다듬어주세요:\n\n{state['draft']}"
    response = await model.ainvoke(
        state["messages"] + [{"role": "user", "content": refine_prompt}]
    )
    return {
        "messages": [response],
        "draft": response.content,
    }


def create_writer_graph() -> StateGraph:
    """라이터 서브그래프를 생성한다."""
    builder = StateGraph(WriterState)

    builder.add_node("write_draft", write_draft)
    builder.add_node("refine", refine)

    builder.add_edge(START, "write_draft")
    builder.add_edge("write_draft", "refine")
    builder.add_edge("refine", END)

    return builder.compile()
```

### 9.2.3 State 공유 전략

서브그래프는 메인 그래프와 State를 공유할 때 두 가지 전략을 선택할 수 있다:

| 전략 | 설명 | 적합한 경우 |
|---|---|---|
| **전체 State 공유** | 서브그래프가 메인 AgentState를 그대로 사용 | 서브그래프가 메인 State의 대부분을 사용 |
| **부분 State** | 서브그래프 전용 State를 정의하고, 진입/퇴출 시 매핑 | 서브그래프의 관심사가 독립적 |

통합 아키텍처에서는 **부분 State를 권장**한다. 서브그래프의 독립성을 유지하고, 서브그래프 단독 테스트를 용이하게 하기 때문이다.

### 9.2.4 서브그래프 간 통신

서브그래프끼리 직접 통신하지 않는다. 모든 통신은 메인 그래프를 통해 이루어진다:

```
researcher 서브그래프 → (결과를 메인 State에 기록)
                          ↓
                    메인 그래프의 라우팅
                          ↓
writer 서브그래프 ← (메인 State에서 researcher 결과 읽기)
```

---

## 9.3 메인 그래프 조립 (main.py)

### 9.3.1 조립 3단계

메인 그래프 조립은 **노드 등록 → 엣지 연결 → 컴파일** 3단계로 이루어진다:

```python
# graphs/main.py

from langgraph.graph import StateGraph, START, END
from core.state import AgentState
from nodes.reasoning import think
from nodes.execution import execute_tools
from nodes.routing import should_continue
from graphs.builder import compile_graph


def create_graph(checkpointer=None, store=None):
    """메인 에이전트 그래프를 생성한다.

    Args:
        checkpointer: 상태 영속화 체크포인터 (선택)
        store: 장기 메모리 저장소 (선택)

    Returns:
        컴파일된 그래프
    """
    # ── 1단계: 그래프 생성 ──
    builder = StateGraph(AgentState)

    # ── 2단계: 노드 등록 ──
    builder.add_node("think", think)
    builder.add_node("execute_tools", execute_tools)

    # ── 3단계: 엣지 연결 ──
    # 시작 → 추론
    builder.add_edge(START, "think")

    # 추론 후 조건부 분기
    builder.add_conditional_edges(
        "think",
        should_continue,
        {
            "execute_tools": "execute_tools",  # 도구 실행으로
            "respond": END,                     # 최종 답변 → 종료
            "finalize": END,                    # 강제 종료
        },
    )

    # 도구 실행 → 다시 추론 (루프)
    builder.add_edge("execute_tools", "think")

    # ── 4단계: 컴파일 ──
    return compile_graph(builder, checkpointer=checkpointer, store=store)
```

### 9.3.2 그래프 시각화

```
┌───────┐     ┌───────┐     ┌──────────────┐
│ START │────▶│ think │────▶│should_continue│
└───────┘     └───────┘     └──────┬───────┘
                             ┌─────┼─────────┐
                             │     │         │
                      ┌──────▼──┐  │   ┌─────▼────┐
                      │execute  │  │   │ finalize │
                      │_tools   │  │   └─────┬────┘
                      └──┬──────┘  │         │
                         │         ▼         ▼
                         ▼        END       END
                    think (루프)
```

### 9.3.3 체크포인터 주입 시점

체크포인터는 **그래프 컴파일 시** 주입된다. 그래프 로직은 체크포인터의 구체적 구현을 알지 못한다:

```python
# main.py (실행 진입점) 에서
from graphs.main import create_graph
from memory.checkpointer import get_checkpointer
from memory.store import get_store

# 환경에 맞는 체크포인터와 저장소가 자동으로 선택됨
graph = create_graph(
    checkpointer=get_checkpointer(),
    store=get_store(),
)
```

---

## 9.4 조건부 엣지 전략

### 9.4.1 add_conditional_edges 활용 패턴

`add_conditional_edges`는 라우팅 함수의 반환값에 따라 다음 노드를 결정한다:

```python
builder.add_conditional_edges(
    "think",                    # 출발 노드
    should_continue,            # 라우팅 함수 (routing.py)
    {
        "execute_tools": "execute_tools",  # 반환값: 노드명
        "respond": END,
        "finalize": END,
    },
)
```

### 9.4.2 분기 맵 설계 가이드라인

| 가이드라인 | 설명 |
|---|---|
| **명시적 매핑** | 모든 가능한 반환값을 맵에 명시한다. 누락된 키는 런타임 에러를 유발한다 |
| **END 명시** | 종료 조건은 반드시 `END`로 매핑한다 |
| **기본값 패턴** | 예상치 못한 반환값은 안전한 기본 동작(END 등)으로 매핑한다 |

### 9.4.3 무한 루프 방지 전략

에이전트 그래프에서 가장 흔한 버그는 **무한 루프**이다. 통합 아키텍처에서는 다중 안전장치를 적용한다:

```python
# 1차 안전장치: routing.py의 iteration 체크
def should_continue(state):
    if state.get("iteration", 0) >= 5:
        return "finalize"  # 강제 종료
    ...

# 2차 안전장치: LangGraph의 recursion_limit
graph = create_graph()
result = await graph.ainvoke(
    initial_state,
    config={"recursion_limit": 25},  # 최대 25회 노드 실행
)
```

| 안전장치 | 수준 | 동작 |
|---|---|---|
| `iteration` 카운터 | 비즈니스 로직 | 의미 있는 반복 횟수 제한 |
| `recursion_limit` | 프레임워크 | 절대 상한선, 초과 시 예외 발생 |

---

## graphs/ 레이어 정리

| 파일 | 역할 | 의존 대상 |
|---|---|---|
| `builder.py` | 그래프 조립 유틸리티 | core/ |
| `researcher.py` | 리서처 서브그래프 | core/, tools/, nodes/ |
| `writer.py` | 라이터 서브그래프 | core/, nodes/ |
| `main.py` | 메인 그래프 조립 + 컴파일 | nodes/, memory/, builder.py |

그래프 레이어의 핵심 가치는 **실행 흐름이 코드로 명시적으로 표현**된다는 점이다. `main.py`를 읽으면 에이전트의 전체 동작 흐름을 한눈에 파악할 수 있다.

---

> [← 이전: 제8장 Nodes 레이어](./08-nodes-레이어.md) | [목차](./index.md) | [다음: 제10장 Interfaces 레이어 →](./10-interfaces-레이어.md)
