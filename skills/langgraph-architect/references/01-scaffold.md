# 01 — 프로젝트 스케폴딩

> 작업 전 `assets/architecture-rules.md`를 먼저 읽는다.

---

## 절차

### Step 1 — Phase 결정

사용자에게 시작 Phase를 확인한다.

| Phase | 파일 수 | 포함 레이어 | 적합한 경우 |
|-------|--------|------------|-----------|
| Phase 1 | ~8 | core, prompts, tools, nodes, graphs | 프로토타입, 학습용 |
| Phase 2 | ~14 | Phase 1 + models, base, builder, execution, 서브그래프 | 기능 확장, 멀티에이전트 |
| Phase 3 | ~18 | Phase 2 + memory, interfaces, config | 프로덕션 배포 |

기본값: 명시하지 않으면 **Phase 1**로 시작한다.

### Step 2 — 디렉토리 생성

```bash
# Phase 1 (최소 시작)
mkdir -p agent_system/{core,prompts,tools,nodes,graphs}

# Phase 3 추가 디렉토리
mkdir -p agent_system/{memory,interfaces,config}
```

### Step 3 — Phase 1 필수 파일 생성

#### `core/state.py`

```python
from typing import Annotated, TypedDict
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """에이전트 전역 상태."""
    messages: Annotated[list, add_messages]
    current_plan: str
    iteration: int
    final_answer: str | None
```

#### `core/schemas.py`

```python
from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """에이전트 요청 스키마."""
    query: str = Field(..., min_length=1)
    session_id: str | None = None


class AgentResponse(BaseModel):
    """에이전트 응답 스키마."""
    answer: str
    sources: list[str] = []
```

#### `prompts/templates.py`

```python
SYSTEM_PROMPT = """당신은 유능한 AI 어시스턴트입니다.
사용자의 질문에 정확하고 도움이 되는 답변을 제공합니다."""

PLANNING_PROMPT = """현재 상황을 분석하고 다음 행동을 계획하세요.
사용 가능한 도구: {tools}
컨텍스트: {context}"""
```

#### `tools/__init__.py`

```python
from tools.search import search_tool

TOOL_REGISTRY: dict = {
    "search": search_tool,
}


def get_tools(names: list[str] | None = None) -> list:
    """이름 목록으로 도구를 조회한다. None이면 전체 반환."""
    if names is None:
        return list(TOOL_REGISTRY.values())
    return [TOOL_REGISTRY[n] for n in names]


def get_tool_descriptions() -> str:
    """등록된 도구 설명을 문자열로 반환한다."""
    return "\n".join(
        f"- {name}: {tool.description}"
        for name, tool in TOOL_REGISTRY.items()
    )
```

#### `tools/search.py` (예시 — 프로젝트에 맞게 교체)

```python
from langchain_core.tools import tool


@tool
def search_tool(query: str) -> str:
    """웹에서 정보를 검색한다.

    Args:
        query: 검색할 질의
    """
    # TODO: 실제 검색 API 연동
    return f"'{query}'에 대한 검색 결과입니다."
```

#### `nodes/reasoning.py`

```python
from core.state import AgentState
from prompts.templates import SYSTEM_PROMPT
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from tools import get_tools


async def think(state: AgentState) -> dict:
    """추론 노드: 현재 상황을 분석하고 다음 행동을 결정한다."""
    model = ChatOpenAI(model="gpt-4o", temperature=0)
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
```

#### `nodes/routing.py`

```python
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
```

#### `graphs/main.py`

```python
from langgraph.graph import StateGraph, START, END
from core.state import AgentState
from nodes.reasoning import think
from nodes.routing import should_continue


def create_graph(checkpointer=None):
    """메인 에이전트 그래프를 생성한다."""
    builder = StateGraph(AgentState)

    # 노드 등록
    builder.add_node("think", think)

    # 엣지 연결
    builder.add_edge(START, "think")
    builder.add_conditional_edges(
        "think",
        should_continue,
        {
            "execute_tools": "think",  # Phase 1: execution 미분리, think로 루프
            "respond": END,
            "finalize": END,
        },
    )

    # 컴파일
    kwargs = {}
    if checkpointer is not None:
        kwargs["checkpointer"] = checkpointer
    return builder.compile(**kwargs)
```

#### `main.py` (프로젝트 루트)

```python
import asyncio
from graphs.main import create_graph


async def main():
    graph = create_graph()
    result = await graph.ainvoke({
        "messages": [{"role": "user", "content": "안녕하세요"}],
        "current_plan": "",
        "iteration": 0,
        "final_answer": None,
    })
    print(result.get("final_answer", result["messages"][-1].content))


if __name__ == "__main__":
    asyncio.run(main())
```

#### 각 레이어 `__init__.py`

```python
# core/__init__.py, prompts/__init__.py, nodes/__init__.py, graphs/__init__.py
# 비어있는 __init__.py (내보내기 전용, 로직 없음)
```

### Step 4 — 검증 체크리스트

- [ ] 디렉토리 깊이가 1단계를 초과하지 않는가
- [ ] 모든 레이어 디렉토리에 `__init__.py`가 존재하는가
- [ ] `layers/` 같은 래퍼 디렉토리가 없는가
- [ ] Phase 1에서 memory/, interfaces/, config/ 참조가 없는가
- [ ] `tools/__init__.py`에 TOOL_REGISTRY가 정의되어 있는가

---

## Phase 확장

### Phase 1 → Phase 2

| 순서 | 추가 파일 | 작업 내용 |
|------|----------|----------|
| 1 | `core/models.py` | Model Factory: `get_model()` + 프리셋 (`reasoning_model`, `fast_model`) |
| 2 | `tools/base.py` | 도구 베이스 클래스: `AgentTool(BaseTool)` + 공통 에러 핸들링 |
| 3 | `prompts/builder.py` | 동적 프롬프트 빌더: `build_system_prompt()`, `build_prompt_from_state()` |
| 4 | `nodes/execution.py` | 실행 노드 분리: `ToolNode` 래핑 또는 커스텀 `execute_tools()` |
| 5 | `graphs/<subgraph>.py` | 첫 서브그래프 파일 (예: `graphs/researcher.py`) |
| 6 | `graphs/builder.py` | 그래프 조립 유틸: `create_base_graph()`, `compile_graph()` |
| 7 | — | `reasoning.py`에서 `models.py` 팩토리 사용으로 전환 |
| 8 | — | `graphs/main.py`에 execution 노드 + 서브그래프 연결 |

**핵심 원칙:** 기존 파일의 인터페이스를 변경하지 않는다.

#### `core/models.py` 템플릿

```python
from functools import lru_cache
from langchain_openai import ChatOpenAI


@lru_cache
def get_model(model_name: str = "gpt-4o", temperature: float = 0):
    """모델 팩토리: 동일 파라미터면 캐시된 인스턴스를 반환한다."""
    return ChatOpenAI(model=model_name, temperature=temperature)


reasoning_model = lambda: get_model("gpt-4o", 0)
fast_model = lambda: get_model("gpt-4o-mini", 0)
creative_model = lambda: get_model("gpt-4o", 0.7)
```

#### `nodes/execution.py` 템플릿

```python
from langgraph.prebuilt import ToolNode
from core.state import AgentState
from tools import get_tools

# 방법 1: ToolNode 활용 (단순)
tool_node = ToolNode(tools=get_tools())

# 방법 2: 커스텀 실행 (컨텍스트 누적 필요 시)
async def execute_tools(state: AgentState) -> dict:
    """도구 실행 노드: 추론 노드가 요청한 도구를 실행한다."""
    result = await tool_node.ainvoke(state)
    new_context = []
    for message in result.get("messages", []):
        if hasattr(message, "content") and message.content:
            new_context.append(message.content[:500])
    return {
        "messages": result.get("messages", []),
        "context": new_context,
    }
```

#### `graphs/main.py` Phase 2 업데이트

```python
# Phase 2: execution 노드 추가
from nodes.execution import execute_tools  # 또는 tool_node

builder.add_node("execute_tools", execute_tools)

# 조건부 엣지의 execute_tools를 실제 노드로 연결
builder.add_conditional_edges("think", should_continue, {
    "execute_tools": "execute_tools",  # Phase 1의 "think" 대신 실제 노드
    "respond": END,
    "finalize": END,
})
builder.add_edge("execute_tools", "think")  # 루프
```

### Phase 2 → Phase 3

| 순서 | 추가 레이어 | 작업 내용 |
|------|------------|----------|
| 1 | `config/` | `settings.py` 생성 (Pydantic Settings + `.env`) |
| 2 | `config/agents.yaml` | 에이전트 선언적 구성 파일 |
| 3 | `memory/` | `checkpointer.py` + `store.py` 생성 |
| 4 | `interfaces/` | `api.py` (FastAPI) + `stream.py` (SSE) |
| 5 | — | `core/models.py`에서 `config/settings.py` 참조로 전환 |
| 6 | — | `graphs/main.py`에 체크포인터 주입 |

**핵심 원칙:** 새 레이어는 빈 디렉토리 + `__init__.py`부터 시작한다.
