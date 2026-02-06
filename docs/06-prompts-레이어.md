# 제6장 Prompts 레이어

> [← 이전: 제5장 Memory 레이어](./05-memory-레이어.md) | [목차](./index.md) | [다음: 제7장 Tools 레이어 →](./07-tools-레이어.md)

---

## 이 장의 파일 범위

```
prompts/
├── __init__.py
├── templates.py   ← 6.1
└── builder.py     ← 6.2
```

`prompts/` 레이어는 에이전트의 행동을 결정하는 **프롬프트를 정의하고 조합하는 책임**을 담당한다. 프롬프트를 코드에 직접 문자열로 하드코딩하는 대신, 템플릿으로 분리하고 동적으로 조합하는 패턴을 제공한다.

---

## 6.1 템플릿 설계 (templates.py)

### 6.1.1 설계 원칙

프롬프트 템플릿은 다음 원칙을 따른다:

- **코드와 프롬프트의 분리:** 프롬프트 수정 시 노드 로직을 건드리지 않는다
- **시스템 프롬프트와 사용자 프롬프트의 분리:** 역할 정의와 작업 지시를 구분한다
- **파라미터화:** 동적으로 변하는 부분은 변수로 추출한다

### 6.1.2 프롬프트 상수화 vs 파라미터화 기준

| 기준 | 상수화 (고정) | 파라미터화 (동적) |
|---|---|---|
| **변경 빈도** | 배포 단위로 변경 | 요청마다 변경 |
| **예시** | 시스템 역할 정의, 출력 형식 지침 | 사용자 컨텍스트, 수집된 정보, 도구 목록 |
| **관리 방식** | 상수 문자열 | 템플릿 변수 (`{variable}`) |

### 6.1.3 코드

```python
# prompts/templates.py

"""에이전트 프롬프트 템플릿 모음.

모든 프롬프트 템플릿을 한 파일에서 관리하여
프롬프트 변경 시 수정 위치를 명확하게 한다.
"""

# ──────────────────────────────────────
# 시스템 프롬프트
# ──────────────────────────────────────

SYSTEM_PROMPT = """당신은 사용자의 질문에 정확하게 답변하는 AI 어시스턴트입니다.

## 행동 원칙
- 사용 가능한 도구를 적극 활용하여 정확한 정보를 제공합니다
- 확실하지 않은 정보는 도구를 사용해 확인합니다
- 단계별로 사고하며, 복잡한 질문은 하위 작업으로 분해합니다

## 사용 가능한 도구
{tool_descriptions}

## 응답 형식
- 명확하고 구조화된 한국어로 응답합니다
- 출처가 있는 경우 반드시 명시합니다
"""

# ──────────────────────────────────────
# 추론 프롬프트
# ──────────────────────────────────────

REASONING_PROMPT = """현재까지 수집된 정보를 바탕으로 다음 행동을 결정하세요.

## 현재 계획
{current_plan}

## 수집된 컨텍스트
{context}

## 판단 기준
- 충분한 정보가 있으면 최종 답변을 작성합니다
- 추가 정보가 필요하면 적절한 도구를 호출합니다
- 최대 {max_iterations}회 반복 후에는 현재 정보로 답변합니다
"""

# ──────────────────────────────────────
# 서브그래프별 프롬프트
# ──────────────────────────────────────

RESEARCHER_PROMPT = """당신은 리서치 전문가입니다.
주어진 주제에 대해 정확하고 포괄적인 정보를 수집합니다.

## 리서치 주제
{topic}

## 수집 기준
- 신뢰할 수 있는 출처 우선
- 최신 정보 우선
- 다양한 관점 포함
"""

WRITER_PROMPT = """당신은 기술 문서 작성 전문가입니다.
수집된 정보를 바탕으로 명확하고 구조화된 문서를 작성합니다.

## 작성할 내용
{topic}

## 참고 자료
{research_results}

## 작성 기준
- 대상 독자: {target_audience}
- 톤: 전문적이면서도 이해하기 쉬운
- 구조: 서론 → 본론 → 결론
"""
```

### 6.1.4 템플릿 접근 방식 비교

프롬프트 템플릿을 구현하는 방식은 여러 가지가 있다:

| 방식 | 장점 | 단점 | 채택 여부 |
|---|---|---|---|
| **Python f-string** | 단순, 빠름 | 런타임 에러 감지 어려움 | 기본 채택 |
| **`str.format()`** | 지연 렌더링 가능 | f-string보다 약간 장황 | 기본 채택 |
| **Jinja2** | 조건문/반복문 지원 | 외부 의존성 추가 | 복잡한 템플릿에만 |
| **ChatPromptTemplate** | LangChain 네이티브 | 단순 문자열보다 복잡 | LangChain 깊은 연동 시 |

통합 아키텍처에서는 **`str.format()` 기반의 단순 템플릿**을 기본으로 사용하고, 조건부 분기가 많은 복잡한 프롬프트에 한해 `builder.py`에서 동적으로 조합한다.

---

## 6.2 동적 프롬프트 빌더 (builder.py)

### 6.2.1 네이밍 변경 근거

실용적 접근에서는 이 역할을 `manager.py`로 불렀으나, 통합 아키텍처에서는 **`builder.py`**로 변경한다:

- `manager`는 범용적 이름으로 역할이 모호하다
- `builder`는 "프롬프트를 조립한다"는 구체적 의미를 전달한다
- Builder 패턴과의 일관성을 유지한다 (graphs/builder.py와 동일한 명명 규칙)

### 6.2.2 State 기반 동적 프롬프트 조합

`builder.py`는 현재 State를 기반으로 프롬프트를 동적으로 조합한다:

```python
# prompts/builder.py

from prompts.templates import SYSTEM_PROMPT, REASONING_PROMPT


def build_system_prompt(tool_descriptions: str = "") -> str:
    """시스템 프롬프트를 조립한다.

    Args:
        tool_descriptions: 사용 가능한 도구 설명 문자열
    """
    return SYSTEM_PROMPT.format(
        tool_descriptions=tool_descriptions or "사용 가능한 도구가 없습니다."
    )


def build_reasoning_prompt(
    current_plan: str = "",
    context: list[str] | None = None,
    max_iterations: int = 5,
) -> str:
    """추론 프롬프트를 State 기반으로 조립한다.

    Args:
        current_plan: 현재까지의 계획
        context: 수집된 컨텍스트 리스트
        max_iterations: 최대 반복 횟수
    """
    context_str = "\n".join(context) if context else "아직 수집된 정보가 없습니다."

    return REASONING_PROMPT.format(
        current_plan=current_plan or "아직 계획이 수립되지 않았습니다.",
        context=context_str,
        max_iterations=max_iterations,
    )


def build_prompt_from_state(state: dict, prompt_type: str = "reasoning") -> str:
    """State에서 필요한 정보를 추출하여 프롬프트를 조립한다.

    이 함수는 노드에서 직접 호출하여 State → 프롬프트 변환을 수행한다.
    """
    if prompt_type == "reasoning":
        return build_reasoning_prompt(
            current_plan=state.get("current_plan", ""),
            context=state.get("context", []),
        )
    elif prompt_type == "system":
        return build_system_prompt()
    else:
        raise ValueError(f"알 수 없는 프롬프트 유형: {prompt_type}")
```

### 6.2.3 컨텍스트 주입 패턴

프롬프트에 동적 컨텍스트를 주입하는 일반적인 패턴:

```python
# nodes/reasoning.py 에서의 활용
from langchain_core.messages import SystemMessage, HumanMessage
from prompts.builder import build_system_prompt, build_prompt_from_state
from core.models import reasoning_model

async def think(state: AgentState) -> dict:
    system_prompt = build_system_prompt(tool_descriptions="...")
    reasoning_prompt = build_prompt_from_state(state, "reasoning")

    messages = [
        SystemMessage(content=system_prompt),
        *state["messages"],  # 기존 대화 이력
        HumanMessage(content=reasoning_prompt),  # 추론 지시
    ]

    model = reasoning_model()
    response = await model.ainvoke(messages)
    ...
```

---

## 6.3 버전 관리 전략

프로덕션 환경에서는 프롬프트 변경이 에이전트의 동작에 직접적으로 영향을 미치므로, 체계적인 버전 관리가 필요하다.

### 6.3.1 프롬프트 변경 추적

`templates.py`의 모든 프롬프트에 버전 주석을 달아 변경 이력을 추적한다:

```python
# v1.0: 초기 버전
# v1.1: 도구 사용 지침 강화
# v1.2: 출력 형식 가이드라인 추가
SYSTEM_PROMPT = """..."""
```

Git 기반의 변경 이력 추적이 가장 효과적이며, 프롬프트 파일만 별도로 diff를 확인할 수 있다.

### 6.3.2 A/B 테스트 구조

프롬프트 A/B 테스트가 필요한 경우, `builder.py`에서 버전별 분기를 처리한다:

```python
def build_system_prompt(version: str = "v1", **kwargs) -> str:
    """버전별 시스템 프롬프트 반환"""
    templates = {
        "v1": SYSTEM_PROMPT,
        "v2": SYSTEM_PROMPT_V2,
    }
    template = templates.get(version, SYSTEM_PROMPT)
    return template.format(**kwargs)
```

### 6.3.3 LangSmith 연동 고려사항

LangSmith를 사용하는 경우, 프롬프트를 LangSmith Hub에서 관리하고 런타임에 pull할 수 있다:

```python
# 고급 패턴: LangSmith Hub 연동
from langsmith import hub

def build_system_prompt_from_hub(prompt_name: str = "my-agent-prompt") -> str:
    """LangSmith Hub에서 프롬프트를 가져온다."""
    return hub.pull(prompt_name)
```

이 패턴은 코드 배포 없이 프롬프트를 실시간으로 변경할 수 있는 장점이 있지만, 외부 서비스 의존이 추가되므로 Phase 3 이후에 도입을 고려한다.

---

## prompts/ 레이어 정리

| 파일 | 역할 | 핵심 패턴 |
|---|---|---|
| `templates.py` | 프롬프트 원본 정의 | 상수화된 템플릿 + `{변수}` 슬롯 |
| `builder.py` | State → 프롬프트 동적 조합 | State 기반 컨텍스트 주입 |

프롬프트 레이어의 핵심 가치는 **프롬프트 변경이 노드 로직 변경을 유발하지 않는 것**이다. 템플릿을 수정해도 노드 코드는 그대로이고, 빌더의 조합 로직을 변경해도 템플릿 원문은 그대로이다.

---

> [← 이전: 제5장 Memory 레이어](./05-memory-레이어.md) | [목차](./index.md) | [다음: 제7장 Tools 레이어 →](./07-tools-레이어.md)
