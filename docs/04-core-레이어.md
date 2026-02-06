# 제4장 Core 레이어

> [← 이전: 제3장 전체 구조](./03-전체-구조.md) | [목차](./index.md) | [다음: 제5장 Memory 레이어 →](./05-memory-레이어.md)

---

## 이 장의 파일 범위

```
core/
├── __init__.py
├── state.py       ← 4.1
├── schemas.py     ← 4.2
└── models.py      ← 4.3
```

`core/`는 통합 아키텍처의 **최하위 기반 레이어**이다. 다른 모든 레이어가 `core/`에 의존하지만, `core/` 자체는 외부 레이어를 일절 import하지 않는다. LangGraph, Pydantic 등 외부 라이브러리만 의존한다.

---

## 4.1 State 설계 (state.py)

### 4.1.1 설계 의도

`state.py`는 그래프 실행 중 모든 노드가 공유하는 **단일 상태 객체(State)**를 정의한다. 설계 시 다음 두 가지를 통합했다:

- **실용적 접근의 간결한 TypedDict 기반 State 정의** — 파일 하나에서 State의 전체 형상을 파악할 수 있다
- **엔터프라이즈 접근의 Reducer 개념** — 필드별 병합 전략을 State 정의와 같은 파일에 배치한다

별도의 `reducers.py`나 `validators.py`를 두지 않는다. State와 관련된 모든 것이 `state.py` 하나에 존재한다.

### 4.1.2 Reducer 전략

LangGraph의 **Reducer**는 같은 State 필드에 대해 여러 노드가 값을 쓸 때 충돌을 해소하는 전략 함수이다.

| Reducer 유형 | 동작 | 적용 대상 |
|---|---|---|
| `add_messages` | 메시지 리스트를 지능적으로 누적 (중복 제거 포함) | `messages` 필드 |
| `merge_lists` | 단순 리스트 합치기 (`existing + new`) | `context` 등 커스텀 누적 필드 |
| *(없음 — 덮어쓰기)* | 마지막 값으로 대체 | `current_plan`, `iteration` 등 |

**설계 기준:**
- **누적이 필요한 필드** → Reducer 사용 (`messages`, `context`)
- **최신 값만 유의미한 필드** → Reducer 없이 덮어쓰기 (`current_plan`, `final_answer`)

### 4.1.3 코드

```python
# core/state.py

from typing import Annotated, TypedDict
from langgraph.graph import add_messages


def merge_lists(existing: list, new: list) -> list:
    """커스텀 Reducer: 두 리스트를 단순 합치기"""
    return existing + new


class AgentState(TypedDict):
    """에이전트 그래프의 공유 상태 객체.

    모든 노드는 이 State를 읽고 쓴다.
    Annotated 필드는 Reducer를 통해 값이 누적된다.
    """

    # 대화 이력 — add_messages로 누적
    messages: Annotated[list, add_messages]

    # 수집된 컨텍스트 — merge_lists로 누적
    context: Annotated[list[str], merge_lists]

    # 현재 추론 계획 — 덮어쓰기
    current_plan: str

    # 반복 카운터 — 덮어쓰기
    iteration: int

    # 최종 응답 — 덮어쓰기, None이면 아직 미완
    final_answer: str | None
```

### 4.1.4 확장 가이드

**새 필드 추가 시 Reducer 필요 여부 판단:**

```
필드에 여러 노드가 값을 쓰는가?
├── Yes → 값이 누적되어야 하는가?
│         ├── Yes → Reducer 필요 (merge_lists 또는 커스텀)
│         └── No  → Reducer 없이 덮어쓰기
└── No  → Reducer 불필요
```

**서브그래프별 State 확장:**

서브그래프가 추가 필드를 필요로 할 때, 메인 State를 직접 수정하지 않고 서브그래프 전용 State를 정의할 수 있다:

```python
# graphs/researcher.py 내부
class ResearcherState(TypedDict):
    messages: Annotated[list, add_messages]
    sources: Annotated[list[str], merge_lists]
    query: str
```

메인 State와 서브그래프 State 간의 매핑은 그래프 조립 시 처리한다 ([제9장 Graphs 레이어](./09-graphs-레이어.md) 참조).

---

## 4.2 Schema 설계 (schemas.py)

### 4.2.1 State vs Schema 구분

`state.py`의 State와 `schemas.py`의 Schema는 역할이 명확히 다르다:

| 구분 | State (`state.py`) | Schema (`schemas.py`) |
|---|---|---|
| **용도** | 그래프 내부 흐름용 | 외부 I/O 유효성 검증용 |
| **타입 시스템** | `TypedDict` | Pydantic `BaseModel` |
| **검증** | 런타임 검증 없음 | 입력 시 자동 검증 |
| **사용 위치** | 노드 함수의 매개변수/반환값 | API 엔드포인트, 도구 입출력 |

**왜 분리하는가:** 관심사의 분리 원칙에 따라, 그래프 내부의 데이터 흐름과 외부 인터페이스의 계약(contract)을 독립적으로 관리한다. State에 Pydantic 검증을 넣으면 노드 실행마다 불필요한 검증 오버헤드가 발생한다.

### 4.2.2 Pydantic 모델 설계

```python
# core/schemas.py

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """외부에서 에이전트로 전달되는 요청 스키마"""
    message: str = Field(..., min_length=1, description="사용자 입력 메시지")
    thread_id: str | None = Field(None, description="대화 스레드 ID (기존 대화 이어가기)")
    model: str = Field("gpt-4o", description="사용할 LLM 모델명")


class AgentResponse(BaseModel):
    """에이전트가 외부로 반환하는 응답 스키마"""
    answer: str = Field(..., description="에이전트의 최종 응답")
    thread_id: str = Field(..., description="대화 스레드 ID")
    iterations: int = Field(..., description="추론 반복 횟수")
    tools_used: list[str] = Field(default_factory=list, description="사용된 도구 목록")


class ToolInput(BaseModel):
    """도구 호출 시 공통 입력 스키마"""
    query: str = Field(..., description="도구에 전달할 질의")


class ToolOutput(BaseModel):
    """도구 실행 결과 공통 출력 스키마"""
    result: str = Field(..., description="도구 실행 결과")
    success: bool = Field(True, description="실행 성공 여부")
    error: str | None = Field(None, description="에러 메시지 (실패 시)")
```

### 4.2.3 스키마 활용 예시

```python
# interfaces/api.py에서의 활용
@app.post("/chat", response_model=AgentResponse)
async def chat(request: AgentRequest):
    # AgentRequest가 자동으로 입력을 검증한다
    result = await graph.ainvoke({"messages": [request.message]})
    return AgentResponse(answer=result["final_answer"], ...)
```

---

## 4.3 Model Factory (models.py)

### 4.3.1 채택 근거

`models.py`는 엔터프라이즈 접근에서 가져온 패턴이다. LLM을 직접 인스턴스화하면 다음 문제가 발생한다:

| 문제 | 설명 |
|---|---|
| **API 키 산재** | 모든 LLM 호출 지점에서 `os.environ["OPENAI_API_KEY"]`를 참조 |
| **모델 교체 어려움** | `ChatOpenAI`를 `ChatAnthropic`으로 교체 시 모든 파일 수정 |
| **테스트 곤란** | 실제 LLM을 호출하지 않는 단위 테스트 작성이 어려움 |
| **비용 미제어** | 용도에 맞지 않는 모델을 사용해도 감지하기 어려움 |

팩토리 패턴으로 이 문제를 해결한다:

- **중앙 집중 관리:** 모든 LLM 인스턴스가 한 곳에서 생성된다
- **용도별 프리셋:** reasoning, creative, fast 등 목적에 맞는 사전 설정
- **캐싱:** `@lru_cache`로 동일 설정의 LLM 인스턴스를 재사용한다
- **교체 용이성:** 모델 공급자를 변경해도 팩토리 함수만 수정하면 된다

### 4.3.2 코드

```python
# core/models.py

from functools import lru_cache
from langchain_openai import ChatOpenAI


@lru_cache(maxsize=4)
def get_model(
    model_name: str = "gpt-4o",
    temperature: float = 0,
) -> ChatOpenAI:
    """LLM 인스턴스를 생성하고 캐싱한다.

    동일한 (model_name, temperature) 조합은 같은 인스턴스를 반환한다.
    config/ 레이어가 활성화되면 settings에서 API 키를 가져온다.
    """
    # config/ 레이어가 없는 Phase 1에서는 환경 변수에서 직접 읽기
    try:
        from config.settings import get_settings
        settings = get_settings()
        api_key = settings.openai_api_key
    except ImportError:
        import os
        api_key = os.environ.get("OPENAI_API_KEY")

    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
    )


# 용도별 프리셋
def reasoning_model() -> ChatOpenAI:
    """추론용 모델 — 정확성 우선, temperature=0"""
    return get_model("gpt-4o", 0)


def creative_model() -> ChatOpenAI:
    """창작용 모델 — 다양성 필요, temperature=0.7"""
    return get_model("gpt-4o", 0.7)


def fast_model() -> ChatOpenAI:
    """빠른 응답용 모델 — 비용 최적화"""
    return get_model("gpt-4o-mini", 0)
```

### 4.3.3 멀티 모델 전략

하나의 에이전트 안에서도 노드별로 다른 모델을 사용할 수 있다:

| 노드 | 권장 모델 | 근거 |
|---|---|---|
| `reasoning.py` (think) | `reasoning_model()` | 정확한 추론과 계획 수립 필요 |
| `execution.py` (도구 결과 요약) | `fast_model()` | 도구 결과를 빠르게 정리 |
| 창작형 서브그래프 (writer 등) | `creative_model()` | 다양한 표현 생성 |

**비용 최적화 전략:**

기본적으로 `fast_model()`을 사용하고, 복잡한 추론이 필요한 경우에만 `reasoning_model()`로 에스컬레이션한다:

```python
# nodes/reasoning.py 에서
async def think(state: AgentState) -> dict:
    # 반복 1회차에서는 빠른 모델로 시도
    if state["iteration"] <= 1:
        model = fast_model()
    else:
        model = reasoning_model()
    ...
```

---

## core/ 레이어 정리

| 파일 | 역할 | 의존 대상 |
|---|---|---|
| `state.py` | State 정의 + Reducer | LangGraph |
| `schemas.py` | I/O 스키마 (Pydantic) | Pydantic |
| `models.py` | LLM 팩토리 + 프리셋 | LangChain, config/ (선택적) |

`core/`의 3개 파일은 에이전트 시스템의 **"데이터 타입"과 "모델 인스턴스"를 중앙에서 정의**하는 역할을 한다. 다른 레이어는 이 정의를 import하여 사용하되, `core/`를 수정하지 않는 것이 원칙이다.

---

> [← 이전: 제3장 전체 구조](./03-전체-구조.md) | [목차](./index.md) | [다음: 제5장 Memory 레이어 →](./05-memory-레이어.md)
