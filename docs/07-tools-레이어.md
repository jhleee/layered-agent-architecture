# 제7장 Tools 레이어

> [← 이전: 제6장 Prompts 레이어](./06-prompts-레이어.md) | [목차](./index.md) | [다음: 제8장 Nodes 레이어 →](./08-nodes-레이어.md)

---

## 이 장의 파일 범위

```
tools/
├── __init__.py     # 레지스트리 + 내보내기   ← 7.2
├── base.py         # 도구 베이스 클래스       ← 7.1
├── search.py       # 검색 도구               ← 7.3
├── calculator.py   # 계산기 도구             ← 7.3
└── database.py     # DB 도구                ← 7.3
```

`tools/` 레이어는 에이전트가 사용할 수 있는 **외부 도구(함수)를 정의하고 관리**하는 책임을 담당한다. 실용적 접근의 "도구 1개 = 파일 1개" 원칙과 엔터프라이즈 접근의 레지스트리 패턴을 결합한다.

---

## 7.1 도구 베이스 클래스 (base.py)

### 7.1.1 채택 근거

엔터프라이즈 접근의 `BaseTool` 패턴을 **경량화하여** 채택한다. 모든 도구에 공통으로 필요한 기능을 한 곳에서 제공한다:

- **에러 핸들링 공통화:** 도구 실행 중 예외가 발생하면 일관된 에러 응답을 반환
- **로깅 훅:** 도구 호출/결과를 기록할 수 있는 지점 제공
- **실행 시간 측정:** 성능 모니터링을 위한 기반

### 7.1.2 코드

```python
# tools/base.py

import logging
import time
from functools import wraps
from typing import Callable

logger = logging.getLogger(__name__)


def tool_error_handler(func: Callable) -> Callable:
    """도구 실행의 공통 에러 핸들링 데코레이터.

    도구 함수를 감싸서 예외 발생 시 에러 메시지 문자열을 반환한다.
    LangGraph의 ToolNode는 문자열 반환을 정상 처리하므로,
    에이전트가 에러를 인지하고 다음 행동을 결정할 수 있다.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        tool_name = func.__name__

        try:
            logger.info(f"도구 실행 시작: {tool_name}")
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"도구 실행 완료: {tool_name} ({elapsed:.2f}s)")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"도구 실행 실패: {tool_name} ({elapsed:.2f}s) - {e}")
            return f"도구 '{tool_name}' 실행 중 오류 발생: {str(e)}"

    return wrapper
```

### 7.1.3 @tool 데코레이터 vs 클래스 기반

도구를 정의할 때 두 가지 방식을 선택할 수 있다:

| 방식 | 장점 | 단점 | 권장 시점 |
|---|---|---|---|
| **`@tool` 데코레이터** | 간결, 빠른 정의 | 복잡한 초기화 어려움 | 단순 도구 (대부분의 경우) |
| **클래스 기반 (BaseTool 상속)** | 상태 관리, 초기화 로직 | 보일러플레이트 증가 | DB 연결 등 상태 필요 시 |

통합 아키텍처에서는 **`@tool` 데코레이터를 기본**으로 사용하고, `base.py`의 에러 핸들러를 조합한다.

---

## 7.2 도구 레지스트리 패턴

### 7.2.1 설계 의도

실용적 접근의 flat 구조에서는 도구를 직접 import하여 리스트로 관리했다. 이는 도구가 적을 때는 충분하지만, 도구가 늘어나면 관리가 어려워진다.

통합 아키텍처는 **`__init__.py`를 레지스트리 역할**로 활용한다:

- 도구를 이름 기반으로 등록하고 조회한다
- 특정 도구만 선택적으로 가져올 수 있다
- 새 도구 추가 시 레지스트리에 한 줄만 추가하면 된다

### 7.2.2 코드

```python
# tools/__init__.py

"""도구 레지스트리.

모든 도구의 등록과 조회를 중앙에서 관리한다.
새 도구 추가 시: 1) 파일 생성  2) 여기에 import + 등록
"""

from tools.search import search_tool
from tools.calculator import calculator_tool
from tools.database import database_tool

# ──────────────────────────────────────
# 도구 레지스트리
# ──────────────────────────────────────

TOOL_REGISTRY: dict[str, object] = {
    "search": search_tool,
    "calculator": calculator_tool,
    "database": database_tool,
}


def get_tools(names: list[str] | None = None) -> list:
    """레지스트리에서 도구를 가져온다.

    Args:
        names: 가져올 도구 이름 리스트. None이면 전체 반환.

    Returns:
        도구 객체 리스트
    """
    if names is None:
        return list(TOOL_REGISTRY.values())
    return [TOOL_REGISTRY[name] for name in names if name in TOOL_REGISTRY]


def get_tool_names() -> list[str]:
    """등록된 모든 도구의 이름을 반환한다."""
    return list(TOOL_REGISTRY.keys())


def get_tool_descriptions() -> str:
    """등록된 도구의 설명을 포맷팅하여 반환한다.

    프롬프트에 도구 설명을 주입할 때 사용한다.
    """
    descriptions = []
    for name, tool in TOOL_REGISTRY.items():
        desc = getattr(tool, "description", "설명 없음")
        descriptions.append(f"- {name}: {desc}")
    return "\n".join(descriptions)
```

### 7.2.3 에이전트별 도구 구성

`config/agents.yaml`과 연동하면 에이전트마다 다른 도구 세트를 사용할 수 있다:

```yaml
# config/agents.yaml
agents:
  researcher:
    tools: ["search", "database"]
  calculator_agent:
    tools: ["calculator"]
```

```python
# 에이전트별 도구 로딩
tools = get_tools(agent_config["tools"])
```

---

## 7.3 개별 도구 구현 가이드

### 7.3.1 기본 구조

모든 도구는 동일한 패턴으로 구현한다:

```python
# tools/search.py

from langchain_core.tools import tool
from tools.base import tool_error_handler


@tool
@tool_error_handler
async def search_tool(query: str) -> str:
    """웹 검색을 수행하여 관련 정보를 반환합니다.

    Args:
        query: 검색할 질의 문자열
    """
    # 실제 검색 API 호출 로직
    # 예: Tavily, Google Search, Bing API 등
    results = await perform_search(query)
    return format_search_results(results)
```

```python
# tools/calculator.py

from langchain_core.tools import tool
from tools.base import tool_error_handler


@tool
@tool_error_handler
async def calculator_tool(expression: str) -> str:
    """수학 계산을 수행합니다.

    Args:
        expression: 계산할 수식 문자열 (예: "2 + 3 * 4")
    """
    try:
        # 안전한 수식 평가
        result = eval(expression, {"__builtins__": {}}, {})
        return f"계산 결과: {expression} = {result}"
    except Exception as e:
        return f"계산 오류: {str(e)}"
```

```python
# tools/database.py

from langchain_core.tools import tool
from tools.base import tool_error_handler


@tool
@tool_error_handler
async def database_tool(query: str) -> str:
    """데이터베이스에서 정보를 조회합니다.

    Args:
        query: 자연어 질의 (SQL로 변환되어 실행됨)
    """
    # 자연어 → SQL 변환 및 실행 로직
    results = await execute_db_query(query)
    return format_db_results(results)
```

### 7.3.2 도구 정의 체크리스트

새 도구를 추가할 때 확인할 항목:

- [ ] `@tool` 데코레이터 적용
- [ ] `@tool_error_handler` 적용
- [ ] docstring에 도구 설명 작성 (LLM이 이 설명을 보고 도구 사용 여부를 결정)
- [ ] 매개변수에 타입 힌트와 설명 포함
- [ ] 반환값은 문자열 (LLM이 이해할 수 있는 형태)
- [ ] `tools/__init__.py`의 `TOOL_REGISTRY`에 등록

---

## 7.4 도구 확장 시나리오

### 7.4.1 새 도구 추가 3단계

```
1. 파일 생성     tools/weather.py 에 @tool 함수 정의
                 ↓
2. 레지스트리    tools/__init__.py 의 TOOL_REGISTRY에 등록
   등록          ↓
3. 테스트        도구 단독 테스트 + 에이전트 통합 테스트
```

기존 코드 수정은 `__init__.py`의 레지스트리 한 줄뿐이다.

### 7.4.2 도구 수에 따른 구조 전환 가이드

도구 수가 증가함에 따라 디렉토리 구조를 점진적으로 조정한다:

| 도구 수 | 권장 구조 | 설명 |
|---|---|---|
| **1~10개** | flat (현재 구조) | `tools/search.py`, `tools/calculator.py` |
| **10~30개** | 카테고리 서브폴더 | `tools/web/search.py`, `tools/math/calculator.py` |
| **30개 이상** | 플러그인 시스템 | 도구를 독립 패키지로 분리, 동적 로딩 |

**10~30개 구조 예시:**

```
tools/
├── __init__.py          # 메인 레지스트리 (카테고리별 import)
├── base.py
├── web/
│   ├── __init__.py      # 카테고리 레지스트리
│   ├── search.py
│   └── scraper.py
├── data/
│   ├── __init__.py
│   ├── database.py
│   └── spreadsheet.py
└── math/
    ├── __init__.py
    └── calculator.py
```

**핵심 원칙:** 상위 `__init__.py`의 `get_tools()` 인터페이스는 변하지 않는다. 내부 구조가 어떻게 변하든 호출하는 쪽은 동일한 API를 사용한다.

---

## tools/ 레이어 정리

| 파일 | 역할 | 비고 |
|---|---|---|
| `__init__.py` | 레지스트리 + `get_tools()` API | 새 도구 추가 시 등록 지점 |
| `base.py` | 에러 핸들링 데코레이터 | 모든 도구에 공통 적용 |
| `search.py` 등 | 개별 도구 구현 | 파일 1개 = 도구 1개 |

도구 레이어의 핵심 가치는 **도구 추가가 "파일 생성 + 레지스트리 등록"의 2단계로 완료**되며, 기존 코드에 대한 수정이 최소화된다는 점이다.

---

> [← 이전: 제6장 Prompts 레이어](./06-prompts-레이어.md) | [목차](./index.md) | [다음: 제8장 Nodes 레이어 →](./08-nodes-레이어.md)
