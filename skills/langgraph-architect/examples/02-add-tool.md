# 예시 2: 도구 추가

## 사용자 프롬프트

> "calculator_tool 추가해줘"

## 기대 동작

1. `references/02-tool-creator.md` 참조
2. 두 파일 수정/생성:

### 생성: `tools/calculator.py`

```python
from langchain_core.tools import tool


@tool
def calculator_tool(expression: str) -> str:
    """수학 표현식을 계산한다.

    숫자 계산이 필요할 때 사용한다.
    사칙연산, 거듭제곱 등을 지원한다.

    Args:
        expression: 계산할 수학 표현식 (예: "2 + 3 * 4")
    """
    try:
        import numexpr
        result = numexpr.evaluate(expression)
        return str(result)
    except Exception as e:
        return f"계산 오류: {e}"
```

### 수정: `tools/__init__.py`

```python
from tools.search import search_tool
from tools.calculator import calculator_tool  # 추가

TOOL_REGISTRY: dict = {
    "search": search_tool,
    "calculator": calculator_tool,  # 추가
}
```

## 핵심 검증 항목

- [ ] docstring이 LLM 도구 선택에 충분히 명확한가
- [ ] 에러 시 예외 raise 없이 문자열 반환
- [ ] TOOL_REGISTRY에 등록 완료
- [ ] `tools/`가 `core/`만 import (의존성 준수)
