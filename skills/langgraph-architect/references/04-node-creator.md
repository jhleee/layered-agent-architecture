# 04 — 노드 생성

> 작업 전 `assets/architecture-rules.md`를 먼저 읽는다.

---

## 역할별 코드 템플릿

### Reasoning 노드 (추론 계열)

"무엇을 할지 결정" — LLM 호출 O, 도구 실행 X

```python
# nodes/reasoning.py에 추가
from core.state import AgentState
from core.models import reasoning_model           # Phase 2+
from prompts.builder import build_system_prompt    # Phase 2+
from tools import get_tools, get_tool_descriptions
from langchain_core.messages import SystemMessage, HumanMessage


async def <node_name>(state: AgentState) -> dict:
    """[역할 설명]: 현재 상황을 분석하고 [특정 판단]을 수행한다."""
    # 1. 프롬프트 조립
    system_prompt = build_system_prompt(
        tool_descriptions=get_tool_descriptions()
    )

    # 2. 메시지 구성
    messages = [
        SystemMessage(content=system_prompt),
        *state["messages"],
    ]

    # 3. LLM 호출
    model = reasoning_model()
    model_with_tools = model.bind_tools(get_tools())
    response = await model_with_tools.ainvoke(messages)

    # 4. State 업데이트 반환
    return {
        "messages": [response],
        "current_plan": "...",
        "iteration": state.get("iteration", 0) + 1,
    }
```

### Execution 노드 (실행 계열)

"실제로 수행" — 도구 실행 O, LLM 호출 X

```python
# nodes/execution.py에 추가
from langgraph.prebuilt import ToolNode
from core.state import AgentState
from tools import get_tools


# ToolNode 활용 (단순한 경우)
tool_node = ToolNode(tools=get_tools())


# 커스텀 실행 (결과 가공, 컨텍스트 누적 필요 시)
async def <node_name>(state: AgentState) -> dict:
    """[역할 설명]: [특정 도구]를 실행하고 결과를 처리한다."""
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

### Routing 함수 (라우팅 계열)

"어디로 보낼지 결정" — LLM 호출 X, 도구 실행 X, State 수정 X

```python
# nodes/routing.py에 추가
from core.state import AgentState


def <route_name>(state: AgentState) -> str:
    """[분기 조건 설명]: State를 분석하여 다음 노드를 결정한다.

    Returns:
        "<node_a>" — [조건 A] 일 때
        "<node_b>" — [조건 B] 일 때
        "<default>" — 기본
    """
    # 안전장치: 최대 반복 횟수
    if state.get("iteration", 0) >= 5:
        return "finalize"

    # 분기 로직 (순수 Python, LLM 호출 없음)
    if <condition>:
        return "<node_a>"
    return "<node_b>"
```

---

## 경계 위반 안티패턴

| 위반 | 코드 예시 | 왜 위험한가 | 올바른 방법 |
|------|----------|-----------|-----------|
| reasoning에서 도구 직접 호출 | `think()`에서 `search_tool.invoke()` | 에러 핸들링 누락, 로직 산재 | execution 노드에 위임 |
| execution에서 LLM 호출 | `execute_tools()`에서 `model.invoke()` | 역할 경계 침범 | reasoning 노드에 위임 |
| execution에서 라우팅 판단 | `execute_tools()`에서 다음 노드 결정 | 흐름 분산, 디버깅 곤란 | routing 함수로 분리 |
| routing에서 LLM 호출 | `should_continue()`에서 `model.invoke()` | 비결정적, 비용 증가 | State 기반 순수 함수 유지 |
| routing에서 State 수정 | `should_continue()`에서 State 업데이트 | 부작용 발생 | 문자열 반환만 수행 |

---

## 기존 파일에 추가 vs 새 파일 생성

| 판단 기준 | 기존 파일에 함수 추가 | 새 파일 생성 |
|----------|-------------------|-----------|
| 같은 역할 계열 | reasoning 노드 → `reasoning.py`에 추가 | — |
| 다른 역할 계열 | — | 새 계열이면 `nodes/<new_role>.py` 생성 |
| 파일이 200줄 초과 | — | 기능 단위로 파일 분리 고려 |
| 특정 서브그래프 전용 | — | 해당 서브그래프 파일 내 또는 전용 노드 파일 |

**기본 원칙:** 기존 3파일 (reasoning/execution/routing)에 함수를 추가한다. 파일이 커지면 분리한다.

---

## 그래프 연결

새 노드를 생성한 후 반드시 `graphs/main.py`에 등록한다.

### 일반 노드 추가

```python
# graphs/main.py
from nodes.reasoning import <new_node>

builder.add_node("<new_node>", <new_node>)
builder.add_edge("<prev_node>", "<new_node>")
```

### 조건부 엣지에 분기 추가

```python
# graphs/main.py — 기존 조건부 엣지의 맵에 추가
builder.add_conditional_edges(
    "think",
    should_continue,
    {
        "execute_tools": "execute_tools",
        "<new_route>": "<new_node>",  # 추가
        "respond": END,
        "finalize": END,
    },
)
```

---

## 검증 체크리스트

- [ ] 노드 역할이 경계를 준수하는가 (reasoning/execution/routing)
- [ ] 반환값이 State 업데이트를 위한 부분 딕셔너리인가
- [ ] 모든 노드가 `AgentState`를 입력으로 받는가
- [ ] `graphs/main.py`에 노드가 등록되어 있는가
- [ ] 엣지가 올바르게 연결되어 있는가
- [ ] 안전장치 (iteration 체크)가 포함되어 있는가
- [ ] 의존성 방향 위반이 없는가 (nodes/는 core, prompts, tools만 import)
