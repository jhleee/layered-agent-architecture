# 제8장 Nodes 레이어

> [← 이전: 제7장 Tools 레이어](./07-tools-레이어.md) | [목차](./index.md) | [다음: 제9장 Graphs 레이어 →](./09-graphs-레이어.md)

---

## 이 장의 파일 범위

```
nodes/
├── __init__.py
├── reasoning.py   ← 8.1
├── execution.py   ← 8.2
└── routing.py     ← 8.3
```

`nodes/` 레이어는 에이전트의 **실질적인 처리 로직**이 위치하는 곳이다. 그래프의 각 노드가 수행하는 구체적인 작업 — 추론, 도구 실행, 라우팅 — 을 파일 단위로 분리한다.

---

## 핵심 설계 결정: 왜 역할별 파일 분리인가

엔터프라이즈 접근에서는 `nodes.py` 한 파일에 모든 노드를 통합하고, 전략 패턴(`strategies.py`)으로 행동을 분기했다. 통합 아키텍처에서는 **역할별 파일 분리**를 채택한다.

### 비교

| 접근 | 구조 | 장점 | 단점 |
|---|---|---|---|
| **통합 방식** (B) | `nodes.py` + `strategies.py` | 파일 수 적음 | 역할 찾기 어려움, 파일 비대화 |
| **분리 방식** (채택) | `reasoning.py` + `execution.py` + `routing.py` | 역할 즉시 파악 | import 경로 약간 증가 |

**분리를 선택한 근거:**

- **파일명 = 역할:** `reasoning.py`를 열면 추론 로직만 있다. `execution.py`를 열면 도구 실행 로직만 있다.
- **독립 테스트:** 각 파일을 독립적으로 테스트할 수 있다.
- **변경 격리:** 추론 로직을 수정해도 실행 로직에 영향이 없다.
- **import 경로 증가는 수용 가능:** `from nodes.reasoning import think` vs `from nodes import think`의 차이는 미미하다.

---

## 8.1 추론 노드 (reasoning.py)

### 8.1.1 역할

`reasoning.py`는 에이전트의 **"사고"를 담당**한다:
- 현재 상황을 분석한다
- 다음 행동 계획을 수립한다
- LLM을 호출하여 추론 결과를 생성한다

추론 노드는 도구를 **직접 실행하지 않는다**. 도구 호출이 필요하다고 판단하면 `tool_calls`를 포함한 메시지를 반환하고, 실제 실행은 `execution.py`가 처리한다.

### 8.1.2 연동 관계

```
                ┌────────────────┐
                │  reasoning.py  │
                │    (think)     │
                └───────┬────────┘
                        │ 의존
            ┌───────────┼───────────┐
            │           │           │
   ┌────────▼──┐  ┌─────▼────┐  ┌──▼───────┐
   │core/models│  │ prompts/ │  │core/state│
   │  .py      │  │builder.py│  │  .py     │
   └───────────┘  └──────────┘  └──────────┘
```

### 8.1.3 코드

```python
# nodes/reasoning.py

from langchain_core.messages import SystemMessage, HumanMessage
from core.state import AgentState
from core.models import reasoning_model
from prompts.builder import build_system_prompt, build_prompt_from_state
from tools import get_tools, get_tool_descriptions


async def think(state: AgentState) -> dict:
    """추론 노드: 현재 State를 분석하고 다음 행동을 결정한다.

    Returns:
        State 업데이트 딕셔너리:
        - messages: LLM 응답 (도구 호출 포함 가능)
        - current_plan: 현재 추론 계획
        - iteration: 반복 카운터 증가
    """
    # 1. 프롬프트 조립
    system_prompt = build_system_prompt(
        tool_descriptions=get_tool_descriptions()
    )
    reasoning_context = build_prompt_from_state(state, "reasoning")

    # 2. 메시지 구성
    messages = [
        SystemMessage(content=system_prompt),
        *state["messages"],
    ]

    # iteration이 1 이상이면 추론 컨텍스트 추가
    if state.get("iteration", 0) > 0:
        messages.append(HumanMessage(content=reasoning_context))

    # 3. LLM 호출 (도구 바인딩)
    model = reasoning_model()
    model_with_tools = model.bind_tools(get_tools())
    response = await model_with_tools.ainvoke(messages)

    # 4. 계획 추출 (도구 호출이 있으면 "도구 사용", 없으면 "답변 준비")
    has_tool_calls = bool(response.tool_calls)
    plan = "도구 호출 후 결과 분석 필요" if has_tool_calls else "최종 답변 준비 완료"

    return {
        "messages": [response],
        "current_plan": plan,
        "iteration": state.get("iteration", 0) + 1,
    }
```

### 8.1.4 반환값 설계

`think` 함수의 반환값은 State의 일부 필드를 업데이트하는 딕셔너리이다:

| 반환 필드 | Reducer | 동작 |
|---|---|---|
| `messages` | `add_messages` | LLM 응답이 대화 이력에 **누적** |
| `current_plan` | *(없음)* | 최신 계획으로 **덮어쓰기** |
| `iteration` | *(없음)* | 카운터 **덮어쓰기** |

---

## 8.2 실행 노드 (execution.py)

### 8.2.1 역할

`execution.py`는 에이전트의 **"행동"을 담당**한다:
- 추론 노드가 요청한 도구를 실제로 실행한다
- 도구 실행 결과를 State에 반영한다
- 에러 발생 시 적절한 에러 메시지를 반환한다

### 8.2.2 ToolNode 래핑 vs 커스텀 실행

LangGraph는 `ToolNode`라는 내장 노드를 제공하여 도구 실행을 자동화한다. 통합 아키텍처에서는 **상황에 따라 선택**한다:

| 방식 | 장점 | 단점 | 권장 시점 |
|---|---|---|---|
| **ToolNode (내장)** | 설정 최소, 자동 에러 처리 | 커스터마이징 제한 | 단순 도구 실행 |
| **커스텀 실행** | 전처리/후처리 자유 | 직접 구현 필요 | 결과 가공, 로깅, 컨텍스트 누적 필요 시 |

### 8.2.3 코드

```python
# nodes/execution.py

from langgraph.prebuilt import ToolNode
from core.state import AgentState
from tools import get_tools


# 방법 1: ToolNode 활용 (단순한 경우)
tool_node = ToolNode(tools=get_tools())


# 방법 2: 커스텀 실행 (컨텍스트 누적이 필요한 경우)
async def execute_tools(state: AgentState) -> dict:
    """도구 실행 노드: 추론 노드가 요청한 도구를 실행한다.

    도구 실행 결과를 messages에 추가하고,
    주요 결과를 context에도 누적한다.
    """
    # ToolNode로 기본 실행
    result = await tool_node.ainvoke(state)

    # 도구 결과에서 컨텍스트 추출
    new_context = []
    for message in result.get("messages", []):
        if hasattr(message, "content") and message.content:
            # 도구 결과의 핵심 내용을 컨텍스트에 누적
            new_context.append(message.content[:500])  # 최대 500자

    return {
        "messages": result.get("messages", []),
        "context": new_context,
    }
```

### 8.2.4 에러 핸들링 전략

도구 실행 중 에러가 발생하면, 에이전트가 이를 인지하고 대안을 선택할 수 있도록 **에러를 메시지로 변환**한다:

```python
# 에러 발생 시 흐름
think → "search 도구 호출"
         ↓
execute_tools → 에러 발생: "API 연결 실패"
         ↓
think (재진입) → 에러를 인지하고 다른 도구 사용 또는 답변 생성
```

에러를 예외로 전파하지 않고 메시지로 변환하는 이유는, 에이전트가 에러 상황에서도 **자율적으로 판단**할 수 있어야 하기 때문이다.

---

## 8.3 라우팅 로직 (routing.py)

### 8.3.1 역할

`routing.py`는 에이전트의 **"방향 결정"을 담당**한다:
- 조건부 엣지의 분기 결정 함수를 정의한다
- State를 분석하여 다음에 실행할 노드를 결정한다
- LLM을 호출하지 않는다 — 순수한 Python 로직만 사용한다

### 8.3.2 엔터프라이즈 접근의 strategies.py를 대체하는 근거

엔터프라이즈 접근의 `strategies.py`는 라우팅 전략을 전략 패턴으로 추상화했으나, 통합 아키텍처에서는 이를 **routing.py에 직접 함수로 정의**한다:

- 전략 패턴의 추상 클래스/인터페이스 오버헤드 제거
- 라우팅 로직이 함수 단위로 명확히 분리
- 새 라우팅 규칙 추가가 "함수 추가"로 완료

### 8.3.3 코드

```python
# nodes/routing.py

from core.state import AgentState

# ──────────────────────────────────────
# 메인 그래프 라우팅
# ──────────────────────────────────────

def should_continue(state: AgentState) -> str:
    """메인 그래프의 핵심 라우팅 함수.

    think 노드 실행 후 다음 행동을 결정한다.

    Returns:
        "execute_tools" — 도구 호출이 필요한 경우
        "respond"       — 최종 답변을 반환할 경우
        "finalize"      — 최대 반복 횟수 도달 시 강제 종료
    """
    messages = state.get("messages", [])
    iteration = state.get("iteration", 0)

    # 안전장치: 최대 반복 횟수 초과 시 강제 종료
    if iteration >= 5:
        return "finalize"

    # 마지막 메시지 확인
    if not messages:
        return "respond"

    last_message = messages[-1]

    # 도구 호출이 있으면 실행으로
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tools"

    # 도구 호출이 없으면 최종 답변
    return "respond"


# ──────────────────────────────────────
# 서브그래프 라우팅 (멀티 에이전트)
# ──────────────────────────────────────

def select_subgraph(state: AgentState) -> str:
    """서브그래프 선택 라우팅 함수.

    사용자 요청의 유형에 따라 적절한 서브그래프로 분기한다.

    Returns:
        "researcher" — 정보 수집이 필요한 경우
        "writer"     — 문서 작성이 필요한 경우
        "direct"     — 직접 답변 가능한 경우
    """
    plan = state.get("current_plan", "")

    if "검색" in plan or "조사" in plan or "research" in plan.lower():
        return "researcher"
    elif "작성" in plan or "문서" in plan or "write" in plan.lower():
        return "writer"
    else:
        return "direct"
```

### 8.3.4 라우팅 함수 설계 원칙

| 원칙 | 설명 |
|---|---|
| **순수 함수** | 외부 상태를 변경하지 않고, State만 읽어서 문자열을 반환한다 |
| **LLM 미호출** | 라우팅은 결정적(deterministic)이어야 한다. LLM 호출은 비용과 지연을 추가한다 |
| **문자열 반환** | 반환값은 `add_conditional_edges`의 라우팅 맵 키와 일치해야 한다 |
| **안전장치 포함** | 무한 루프 방지를 위한 `iteration` 체크를 반드시 포함한다 |

---

## 8.4 노드 간 책임 경계

### 책임 경계 다이어그램

```
┌──────────────────────────────────────────────────┐
│  reasoning.py  │  "무엇을 할지 결정"               │
│                │  LLM 호출 ✅ | 도구 실행 ❌        │
├────────────────┤                                  │
│  routing.py    │  "어디로 보낼지 결정"              │
│                │  LLM 호출 ❌ | 도구 실행 ❌        │
├────────────────┤                                  │
│  execution.py  │  "실제로 수행"                    │
│                │  LLM 호출 ❌ | 도구 실행 ✅        │
└──────────────────────────────────────────────────┘
```

### 경계 위반 안티패턴

| 위반 | 설명 | 왜 위험한가 |
|---|---|---|
| reasoning에서 도구 직접 호출 | think 함수 안에서 `search_tool.invoke(...)` | 도구 실행 로직이 산재되어 에러 핸들링 누락 위험 |
| execution에서 라우팅 판단 | execute_tools 안에서 다음 노드 결정 | 라우팅 로직이 분산되어 흐름 파악 곤란 |
| routing에서 LLM 호출 | should_continue에서 LLM으로 분기 판단 | 비용 증가, 비결정적 라우팅으로 디버깅 어려움 |

이 경계를 준수하면 각 파일의 역할이 명확해지고, 수정 시 영향 범위를 정확히 예측할 수 있다.

---

## nodes/ 레이어 정리

| 파일 | 역할 | 호출하는 대상 | 호출하지 않는 것 |
|---|---|---|---|
| `reasoning.py` | 추론, 계획 수립 | LLM (model factory), 프롬프트 (builder) | 도구 직접 실행 |
| `execution.py` | 도구 실행, 결과 처리 | ToolNode, 도구 함수 | LLM, 라우팅 판단 |
| `routing.py` | 분기 결정 | State 읽기 전용 | LLM, 도구, State 수정 |

---

> [← 이전: 제7장 Tools 레이어](./07-tools-레이어.md) | [목차](./index.md) | [다음: 제9장 Graphs 레이어 →](./09-graphs-레이어.md)
