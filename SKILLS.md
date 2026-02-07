# SKILLS — 아키텍처 구현 지침

> 이 문서는 [통합 아키텍처](./README.md)를 기반으로 코드를 생성·확장할 때 따라야 하는 구체적인 절차와 규칙을 정의한다.

---

## 목차

1. [공통 규칙](#1-공통-규칙)
2. [SKILL: 프로젝트 스케폴딩](#2-skill-프로젝트-스케폴딩)
3. [SKILL: 레이어 생성](#3-skill-레이어-생성)
4. [SKILL: 도구 추가](#4-skill-도구-추가)
5. [SKILL: 서브그래프 추가](#5-skill-서브그래프-추가)
6. [SKILL: Phase 확장](#6-skill-phase-확장)
7. [SKILL: 노드 작성](#7-skill-노드-작성)
8. [검증 체크리스트](#8-검증-체크리스트)

---

## 1. 공통 규칙

모든 SKILL 실행 시 반드시 준수해야 하는 규칙이다.

### 1.1 참조 문서

작업 전 반드시 해당 레이어의 설계 문서를 참조한다.

| 레이어 | 참조 문서 |
|--------|----------|
| core/ | [docs/04-core-레이어.md](./docs/04-core-레이어.md) |
| memory/ | [docs/05-memory-레이어.md](./docs/05-memory-레이어.md) |
| prompts/ | [docs/06-prompts-레이어.md](./docs/06-prompts-레이어.md) |
| tools/ | [docs/07-tools-레이어.md](./docs/07-tools-레이어.md) |
| nodes/ | [docs/08-nodes-레이어.md](./docs/08-nodes-레이어.md) |
| graphs/ | [docs/09-graphs-레이어.md](./docs/09-graphs-레이어.md) |
| interfaces/ | [docs/10-interfaces-레이어.md](./docs/10-interfaces-레이어.md) |
| config/ | [docs/11-config-레이어.md](./docs/11-config-레이어.md) |

### 1.2 의존성 규칙

```
허용 방향 (상위 → 하위만 import 가능):

main.py → interfaces/ → graphs/ → nodes/ → prompts/, tools/, core/
                                 → memory/, config/
```

**금지 사항:**
- 하위 레이어에서 상위 레이어 import 금지 (예: core/에서 nodes/ import 금지)
- 순환 의존 발생 시 공통 요소를 core/로 추출
- 동일 레벨 레이어 간 import는 의존성 다이어그램 확인 후 허용 여부 판단

### 1.3 네이밍 규칙

| 대상 | 규칙 | 예시 |
|------|------|------|
| 디렉토리 | 소문자, 복수형 | `tools/`, `nodes/`, `graphs/` |
| 파일 | 소문자, snake_case | `reasoning.py`, `check_pointer.py` |
| 클래스 | PascalCase | `AgentState`, `SearchTool` |
| 함수 | snake_case | `get_model()`, `should_continue()` |
| 상수 | UPPER_SNAKE_CASE | `TOOL_REGISTRY`, `SYSTEM_PROMPT` |

### 1.4 파일 구조 원칙

- **1 폴더 = 1 레이어**: `layers/` 같은 래퍼 디렉토리 생성 금지
- **1 파일 = 1 역할**: 하나의 파일에 여러 관심사를 섞지 않는다
- **네스팅 깊이 최대 1**: `agent_system/<layer>/<file>.py` 이상 깊어지지 않는다
- **`__init__.py`는 내보내기 전용**: 로직을 넣지 않는다 (tools/의 레지스트리 제외)

---

## 2. SKILL: 프로젝트 스케폴딩

> 빈 프로젝트에서 통합 아키텍처의 디렉토리 구조를 생성한다.

### 절차

**Step 1 — Phase 결정**

사용자에게 시작 Phase를 확인한다.

| Phase | 파일 수 | 포함 레이어 |
|-------|---------|------------|
| Phase 1 | ~8 | core/, prompts/, tools/, nodes/, graphs/ |
| Phase 2 | ~14 | Phase 1 + models.py, base.py, builder.py, execution.py, 서브그래프 |
| Phase 3 | ~18 | Phase 2 + memory/, interfaces/, config/ |

**Step 2 — 디렉토리 생성**

Phase에 따라 필요한 디렉토리만 생성한다.

```bash
# Phase 1 (최소 시작)
mkdir -p agent_system/{core,prompts,tools,nodes,graphs}

# Phase 2 (기능 확장) — Phase 1 + 동일 디렉토리에 파일 추가

# Phase 3 (프로덕션) — 추가 디렉토리
mkdir -p agent_system/{memory,interfaces,config}
```

**Step 3 — 필수 파일 생성**

Phase 1 필수 파일 목록:

```
agent_system/
├── core/
│   ├── __init__.py
│   ├── state.py           # AgentState 정의 + Reducer
│   └── schemas.py         # Pydantic 요청/응답 모델
├── prompts/
│   ├── __init__.py
│   └── templates.py       # 시스템/사용자 프롬프트 상수
├── tools/
│   ├── __init__.py        # TOOL_REGISTRY + get_tools()
│   └── search.py          # 최초 도구 1개
├── nodes/
│   ├── __init__.py
│   ├── reasoning.py       # think 노드
│   └── routing.py         # should_continue 분기 함수
├── graphs/
│   ├── __init__.py
│   └── main.py            # 메인 그래프 조립 + 컴파일
└── main.py                # 실행 진입점
```

**Step 4 — 빈 `__init__.py` 생성**

각 레이어 디렉토리에 `__init__.py`를 생성한다. tools/만 예외적으로 레지스트리 로직을 포함한다.

**Step 5 — 검증**

[8. 검증 체크리스트](#8-검증-체크리스트)의 구조 검증 항목을 확인한다.

---

## 3. SKILL: 레이어 생성

> 기존 프로젝트에 새 레이어를 추가한다. Phase 확장 시 주로 사용한다.

### 레이어별 생성 템플릿

#### core/ 레이어

```python
# core/state.py
from typing import Annotated, TypedDict
from langgraph.graph import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    current_plan: str
    iteration: int
    final_answer: str | None
```

```python
# core/schemas.py
from pydantic import BaseModel, Field

class AgentRequest(BaseModel):
    query: str = Field(..., min_length=1)
    session_id: str | None = None

class AgentResponse(BaseModel):
    answer: str
    sources: list[str] = []
```

```python
# core/models.py  (Phase 2에서 추가)
from functools import lru_cache
from langchain_openai import ChatOpenAI

@lru_cache
def get_model(model_name: str = "gpt-4o", temperature: float = 0):
    return ChatOpenAI(model=model_name, temperature=temperature)

reasoning_model = lambda: get_model("gpt-4o", 0)
fast_model = lambda: get_model("gpt-4o-mini", 0)
```

#### memory/ 레이어

```python
# memory/checkpointer.py
from langgraph.checkpoint.memory import MemorySaver

def get_checkpointer():
    """환경에 따라 적절한 체크포인터를 반환한다."""
    # Phase 3: settings.py에서 환경 정보를 읽어 분기
    return MemorySaver()
```

```python
# memory/store.py
from langgraph.store.memory import InMemoryStore

def get_store():
    """환경에 따라 적절한 저장소를 반환한다."""
    return InMemoryStore()
```

#### prompts/ 레이어

```python
# prompts/templates.py
SYSTEM_PROMPT = """당신은 유능한 AI 어시스턴트입니다.
사용자의 질문에 정확하고 도움이 되는 답변을 제공합니다."""

PLANNING_PROMPT = """현재 상황을 분석하고 다음 행동을 계획하세요.
사용 가능한 도구: {tools}
컨텍스트: {context}"""
```

```python
# prompts/builder.py  (Phase 2에서 추가)
from prompts.templates import SYSTEM_PROMPT, PLANNING_PROMPT

def build_system_prompt(tools: list[str] | None = None) -> str:
    """State 기반으로 시스템 프롬프트를 동적 조합한다."""
    base = SYSTEM_PROMPT
    if tools:
        base += f"\n\n사용 가능한 도구: {', '.join(tools)}"
    return base
```

#### tools/ 레이어

```python
# tools/__init__.py
from tools.search import search_tool

TOOL_REGISTRY: dict = {
    "search": search_tool,
}

def get_tools(names: list[str] | None = None) -> list:
    """이름 목록으로 도구를 조회한다. None이면 전체 반환."""
    if names is None:
        return list(TOOL_REGISTRY.values())
    return [TOOL_REGISTRY[n] for n in names]
```

```python
# tools/base.py  (Phase 2에서 추가)
from langchain_core.tools import BaseTool
import logging

logger = logging.getLogger(__name__)

class AgentTool(BaseTool):
    """공통 에러 핸들링과 로깅을 포함하는 도구 베이스 클래스."""

    def _handle_error(self, error: Exception) -> str:
        logger.error(f"Tool {self.name} failed: {error}")
        return f"도구 실행 중 오류 발생: {error}"
```

#### nodes/ 레이어

```python
# nodes/reasoning.py
from core.state import AgentState

async def think(state: AgentState) -> dict:
    """상황을 분석하고 다음 행동을 계획한다."""
    # model + prompt 조합으로 추론
    ...
    return {"messages": [response], "current_plan": plan}
```

```python
# nodes/routing.py
from core.state import AgentState

def should_continue(state: AgentState) -> str:
    """마지막 메시지를 확인하여 분기를 결정한다."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tools"
    return "respond"
```

```python
# nodes/execution.py  (Phase 2에서 추가)
from langgraph.prebuilt import ToolNode
from tools import get_tools

execute_tools = ToolNode(get_tools())
```

#### graphs/ 레이어

```python
# graphs/main.py
from langgraph.graph import StateGraph, END
from core.state import AgentState
from nodes.reasoning import think
from nodes.routing import should_continue

def build_main_graph():
    graph = StateGraph(AgentState)
    graph.add_node("think", think)
    graph.set_entry_point("think")
    graph.add_conditional_edges("think", should_continue, {
        "execute_tools": "execute_tools",
        "respond": END,
    })
    return graph.compile()
```

#### interfaces/ 레이어

```python
# interfaces/api.py
from fastapi import FastAPI
from core.schemas import AgentRequest, AgentResponse

app = FastAPI()

@app.post("/chat", response_model=AgentResponse)
async def chat(request: AgentRequest):
    """채팅 엔드포인트."""
    ...
```

```python
# interfaces/stream.py
from fastapi.responses import StreamingResponse

async def stream_response(graph, inputs: dict):
    """SSE 스트리밍 응답을 생성한다."""
    async def event_generator():
        async for event in graph.astream_events(inputs, version="v2"):
            yield f"data: {event}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

#### config/ 레이어

```python
# config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    environment: str = "development"
    model_name: str = "gpt-4o"

    class Config:
        env_file = ".env"

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

```yaml
# config/agents.yaml
agents:
  researcher:
    model: gpt-4o
    temperature: 0
    tools:
      - search
      - database
    system_prompt: "research_agent"

  writer:
    model: gpt-4o
    temperature: 0.7
    tools: []
    system_prompt: "writer_agent"
```

---

## 4. SKILL: 도구 추가

> 새로운 도구를 tools/ 레이어에 추가한다.

### 절차

**Step 1 — 도구 파일 생성**

`tools/<tool_name>.py` 파일을 생성한다.

```python
# tools/calculator.py
from langchain_core.tools import tool

@tool
def calculator_tool(expression: str) -> str:
    """수학 표현식을 계산한다.

    Args:
        expression: 계산할 수학 표현식 (예: "2 + 3 * 4")
    """
    try:
        # Using a safe evaluation library like 'numexpr' is strongly recommended
        # to prevent code injection vulnerabilities.
        # For example:
        # import numexpr
        # result = numexpr.evaluate(expression)
        raise NotImplementedError("A safe expression evaluator must be used instead of eval().")
    except Exception as e:
        return f"계산 오류: {e}"
```

**Step 2 — 레지스트리 등록**

`tools/__init__.py`에 import와 레지스트리 항목을 추가한다.

```python
# tools/__init__.py에 추가
from tools.calculator import calculator_tool

TOOL_REGISTRY: dict = {
    "search": search_tool,
    "calculator": calculator_tool,  # ← 추가
}
```

**Step 3 — 검증**

- 도구가 `get_tools()`로 조회되는지 확인
- 도구의 docstring과 args_schema가 정의되어 있는지 확인
- 에러 반환이 문자열로 되는지 확인 (그래프 중단 방지)

### 규칙

- 도구 1개 = 파일 1개 (관련 도구가 2-3개인 경우 같은 파일 허용)
- `@tool` 데코레이터 우선 사용, 복잡한 경우 클래스 기반
- docstring 필수 (LLM이 도구 선택 시 참조)
- 에러 발생 시 예외를 raise하지 말고 에러 메시지 문자열 반환

---

## 5. SKILL: 서브그래프 추가

> 새로운 서브그래프를 graphs/ 레이어에 추가한다.

### 절차

**Step 1 — 서브그래프 파일 생성**

`graphs/<subgraph_name>.py` 파일을 생성한다.

```python
# graphs/researcher.py
from langgraph.graph import StateGraph, END
from core.state import AgentState

def build_researcher_graph():
    """리서처 서브그래프를 빌드한다."""
    graph = StateGraph(AgentState)

    # 서브그래프 고유 노드 등록
    graph.add_node("research", research_node)
    graph.add_node("summarize", summarize_node)

    graph.set_entry_point("research")
    graph.add_edge("research", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile()
```

**Step 2 — 메인 그래프에 연결**

`graphs/main.py`에서 서브그래프를 노드로 등록한다.

```python
# graphs/main.py에서
from graphs.researcher import build_researcher_graph

researcher = build_researcher_graph()
graph.add_node("researcher", researcher)
```

**Step 3 — 라우팅 분기 추가**

`nodes/routing.py`에 서브그래프 라우팅 조건을 추가한다.

### 규칙

- 서브그래프 1개 = 독립 파일 1개
- 서브그래프는 단독으로 compile·테스트 가능해야 한다
- State는 메인 그래프와 공유하되, 서브그래프 전용 필드 추가 가능
- 서브그래프 간 직접 통신 금지 — 반드시 메인 그래프를 경유

---

## 6. SKILL: Phase 확장

> 현재 Phase에서 다음 Phase로 확장한다.

### Phase 1 → Phase 2

| 순서 | 추가 파일 | 작업 내용 |
|------|----------|----------|
| 1 | `core/models.py` | Model Factory 생성, `get_model()` + 프리셋 |
| 2 | `tools/base.py` | 도구 베이스 클래스 생성 |
| 3 | `prompts/builder.py` | 동적 프롬프트 빌더 생성 |
| 4 | `nodes/execution.py` | 실행 노드 분리, ToolNode 래핑 |
| 5 | `graphs/<subgraph>.py` | 첫 서브그래프 파일 생성 |
| 6 | - | `nodes/reasoning.py`에서 models.py의 팩토리 사용으로 전환 |
| 7 | - | `graphs/main.py`에 execution 노드 + 서브그래프 연결 |

### Phase 2 → Phase 3

| 순서 | 추가 레이어 | 작업 내용 |
|------|------------|----------|
| 1 | `config/` | `settings.py` 생성, `.env` 연동 |
| 2 | `memory/` | `checkpointer.py` + `store.py` 생성 |
| 3 | `interfaces/` | `api.py` + `stream.py` 생성 |
| 4 | - | `core/models.py`에서 settings 참조로 전환 |
| 5 | - | `graphs/main.py`에 체크포인터 주입 |
| 6 | `config/agents.yaml` | 에이전트 선언적 구성 파일 생성 |

### 규칙

- Phase 확장 시 **기존 파일의 인터페이스를 변경하지 않는다**
- 새 레이어는 빈 디렉토리 + `__init__.py`부터 시작
- 하드코딩된 값을 config로 추출하는 것은 Phase 3에서 수행

---

## 7. SKILL: 노드 작성

> nodes/ 레이어에 새 노드를 작성한다.

### 노드 유형별 템플릿

#### 추론 노드 (reasoning 계열)

```python
async def <node_name>(state: AgentState) -> dict:
    """[역할 설명]"""
    model = get_model(...)       # core/models.py
    prompt = build_prompt(...)   # prompts/builder.py
    response = await model.ainvoke(prompt)
    return {"messages": [response], "current_plan": "..."}
```

#### 실행 노드 (execution 계열)

```python
async def <node_name>(state: AgentState) -> dict:
    """[역할 설명]"""
    tool_results = ...           # tools/ 호출
    return {"messages": [tool_results]}
```

#### 라우팅 함수 (routing 계열)

```python
def <route_name>(state: AgentState) -> str:
    """[분기 조건 설명]"""
    # State를 읽고 다음 노드 이름을 문자열로 반환
    if condition:
        return "node_a"
    return "node_b"
```

### 규칙

- **reasoning 노드**: LLM 호출 가능, 도구 직접 호출 금지
- **execution 노드**: 도구 호출 가능, LLM 직접 호출 금지
- **routing 함수**: LLM/도구 호출 금지, State 읽기만 수행
- 모든 노드는 `AgentState`를 입력으로 받고 `dict`를 반환
- 반환값은 State 업데이트를 위한 부분 딕셔너리

---

## 8. 검증 체크리스트

모든 SKILL 실행 후 아래 항목을 확인한다.

### 구조 검증

- [ ] 디렉토리 깊이가 1단계를 초과하지 않는가
- [ ] 모든 레이어 디렉토리에 `__init__.py`가 존재하는가
- [ ] `layers/` 같은 래퍼 디렉토리가 없는가

### 의존성 검증

- [ ] 하위 레이어에서 상위 레이어를 import하지 않는가
- [ ] 순환 의존이 없는가
- [ ] core/ 레이어가 외부 레이어를 import하지 않는가

### 네이밍 검증

- [ ] 파일명이 snake_case인가
- [ ] 클래스명이 PascalCase인가
- [ ] 상수가 UPPER_SNAKE_CASE인가

### 기능 검증

- [ ] 새로 추가한 도구가 레지스트리에 등록되어 있는가
- [ ] 새 노드가 그래프에 연결되어 있는가
- [ ] 서브그래프가 단독 compile 가능한가
- [ ] 에러 발생 시 그래프가 중단되지 않고 메시지를 반환하는가

### Phase 정합성 검증

- [ ] 현재 Phase에 포함되지 않는 레이어를 참조하지 않는가
- [ ] Phase 1에서 models.py 없이 동작 가능한가 (하드코딩 허용)
- [ ] Phase 2에서 config/ 없이 동작 가능한가 (기본값 사용)
