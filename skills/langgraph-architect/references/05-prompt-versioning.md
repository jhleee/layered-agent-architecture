# 05 — 프롬프트 버전관리

> 작업 전 `assets/architecture-rules.md`를 먼저 읽는다.

---

## 절차

### Step 1 — templates.py에 버전 추가

```python
# prompts/templates.py

# ── V1 (기본) ──
SYSTEM_PROMPT_V1 = """당신은 유능한 AI 어시스턴트입니다.
사용자의 질문에 정확하고 도움이 되는 답변을 제공합니다."""

# ── V2 (개선) ──
SYSTEM_PROMPT_V2 = """당신은 전문적인 AI 어시스턴트입니다.
단계적으로 사고하고, 근거를 제시하며 답변합니다.
확실하지 않은 내용은 솔직히 모른다고 말합니다."""

# 버전 맵
SYSTEM_PROMPTS = {
    "v1": SYSTEM_PROMPT_V1,
    "v2": SYSTEM_PROMPT_V2,
}

# 기본 버전 (하위 호환)
SYSTEM_PROMPT = SYSTEM_PROMPT_V1
```

### Step 2 — builder.py에서 version 파라미터 분기

```python
# prompts/builder.py

from prompts.templates import SYSTEM_PROMPTS, SYSTEM_PROMPT


def build_system_prompt(
    tool_descriptions: str | None = None,
    version: str = "v1",
) -> str:
    """State 기반으로 시스템 프롬프트를 동적 조합한다.

    Args:
        tool_descriptions: 도구 설명 문자열
        version: 프롬프트 버전 ("v1", "v2", ...)
    """
    base = SYSTEM_PROMPTS.get(version, SYSTEM_PROMPT)

    if tool_descriptions:
        base += f"\n\n사용 가능한 도구:\n{tool_descriptions}"

    return base
```

### Step 3 — 노드에서 버전 선택

```python
# nodes/reasoning.py에서
from prompts.builder import build_system_prompt

async def think(state: AgentState) -> dict:
    # config에서 버전 정보 사용 (Phase 3) 또는 기본값
    prompt_version = state.get("config", {}).get("prompt_version", "v1")
    system_prompt = build_system_prompt(
        tool_descriptions=get_tool_descriptions(),
        version=prompt_version,
    )
    ...
```

---

## A/B 테스트 구조

### 방법 1: config 기반 분기 (Phase 3)

```yaml
# config/agents.yaml
agents:
  default:
    system_prompt_version: "v1"

  experiment_group:
    system_prompt_version: "v2"
```

### 방법 2: thread_id 기반 분기

```python
def select_prompt_version(thread_id: str) -> str:
    """thread_id 해시 기반으로 A/B 그룹 결정."""
    return "v2" if hash(thread_id) % 2 == 0 else "v1"
```

### 방법 3: LangSmith Hub 연동 (Phase 3+ 선택)

```python
# LangSmith Hub에서 프롬프트 가져오기
from langchain import hub

prompt = hub.pull("my-org/agent-prompt:v2")
```

LangSmith Hub는 프롬프트의 원격 버전 관리를 제공한다. 코드 배포 없이 프롬프트를 업데이트할 수 있다.

---

## 버전 관리 규칙

- **기존 버전을 수정하지 않는다** — 새 버전을 추가한다 (V1 유지, V2 추가)
- **기본 버전을 항상 유지한다** — `SYSTEM_PROMPT = SYSTEM_PROMPT_V1` (하위 호환)
- **버전 맵을 사용한다** — `SYSTEM_PROMPTS` 딕셔너리로 버전 조회
- **prompts/는 core/만 import 가능** — 의존성 방향 준수

---

## 검증 체크리스트

- [ ] 기존 V1 프롬프트가 변경되지 않았는가
- [ ] `SYSTEM_PROMPTS` 맵에 새 버전이 등록되어 있는가
- [ ] `build_system_prompt()`에 `version` 파라미터가 추가되어 있는가
- [ ] 기본 `SYSTEM_PROMPT` 상수가 유지되어 있는가 (하위 호환)
- [ ] 의존성 방향 위반이 없는가
