# 02 — 도구 추가

> 작업 전 `assets/architecture-rules.md`를 먼저 읽는다.

---

## 절차

### Step 1 — 도구 파일 생성

`tools/<tool_name>.py` 파일을 생성한다.

```python
# tools/<tool_name>.py
from langchain_core.tools import tool


@tool
def <tool_name>_tool(<param>: <type>) -> str:
    """도구 설명 — LLM이 도구 선택 시 이 docstring을 참조한다.

    구체적으로 어떤 상황에서 이 도구를 사용해야 하는지 기술한다.
    입력 파라미터와 반환값의 의미를 명시한다.

    Args:
        <param>: 파라미터 설명
    """
    try:
        # 도구 로직
        result = ...
        return str(result)
    except Exception as e:
        return f"도구 실행 오류: {e}"
```

### Step 2 — 레지스트리 등록

`tools/__init__.py`에 import와 레지스트리 항목을 추가한다.

```python
# tools/__init__.py
from tools.search import search_tool
from tools.<tool_name> import <tool_name>_tool  # 추가

TOOL_REGISTRY: dict = {
    "search": search_tool,
    "<tool_name>": <tool_name>_tool,  # 추가
}
```

### Step 3 — 검증

- [ ] `get_tools()`로 새 도구가 조회되는가
- [ ] docstring이 명확한가 (LLM이 언제 사용할지 판단 가능)
- [ ] `args_schema`가 정의되어 있는가 (`@tool`은 자동 생성)
- [ ] 에러 시 예외를 raise하지 않고 문자열을 반환하는가
- [ ] 의존성 방향 위반이 없는가 (tools/는 core/만 import 가능)

---

## 에러 핸들링 패턴

도구는 예외를 raise하면 안 된다 — 그래프가 중단된다. 대신 에러 메시지를 문자열로 반환한다.

```python
@tool
def risky_tool(query: str) -> str:
    """외부 API를 호출하는 도구."""
    try:
        response = call_external_api(query)
        return response
    except ConnectionError:
        return "외부 API 연결에 실패했습니다. 잠시 후 다시 시도하세요."
    except Exception as e:
        return f"도구 실행 중 예상치 못한 오류: {e}"
```

Phase 2 이상에서는 `tools/base.py`의 `AgentTool` 베이스 클래스를 사용하여 공통 에러 핸들링을 적용할 수 있다:

```python
# tools/base.py (Phase 2+)
from langchain_core.tools import BaseTool
import logging

logger = logging.getLogger(__name__)

class AgentTool(BaseTool):
    """공통 에러 핸들링과 로깅을 포함하는 도구 베이스 클래스."""

    def _handle_error(self, error: Exception) -> str:
        logger.error(f"Tool {self.name} failed: {error}")
        return f"도구 실행 중 오류 발생: {error}"
```

---

## Docstring 작성 가이드

LLM은 docstring을 읽고 도구를 선택한다. 좋은 docstring의 특징:

| 요소 | 나쁜 예 | 좋은 예 |
|------|--------|--------|
| 역할 | "검색한다" | "웹에서 최신 정보를 검색하여 텍스트로 반환한다" |
| 사용 시점 | (없음) | "실시간 정보가 필요하거나 학습 데이터에 없는 내용을 조회할 때 사용" |
| 파라미터 | `query: str` | `query: 검색할 키워드 또는 자연어 질문` |
| 반환값 | (없음) | "검색 결과 텍스트. 결과가 없으면 '결과 없음' 반환" |

---

## 규칙

- **1 도구 = 1 파일** (관련 도구 2-3개는 같은 파일 허용)
- **`@tool` 데코레이터 우선** — 복잡한 경우만 클래스 기반
- **docstring 필수** — LLM 도구 선택의 핵심 참조 정보
- **에러 → 문자열 반환** — 예외 raise 금지
- **`tools/`는 `core/`만 import 가능** — nodes/, graphs/ 등 import 금지
