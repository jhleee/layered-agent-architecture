# 예시 1: 프로젝트 스케폴딩

## 사용자 프롬프트

> "langgraph로 날씨 봇 만들어줘"

## 기대 동작

1. `references/01-scaffold.md` 참조
2. `scaffolding/` 디렉토리를 프로젝트에 복사
3. 프로젝트에 맞게 커스터마이즈:

### 수정: `core/state.py` — 날씨 봇 전용 필드 추가

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    current_plan: str
    iteration: int
    final_answer: str | None
    location: str | None          # 추가
```

### 수정: `tools/search.py` → `tools/weather.py`로 교체

```python
@tool
def weather_tool(location: str) -> str:
    """지정한 위치의 현재 날씨를 조회한다."""
    # TODO: 실제 날씨 API 연동
    return f"{location}의 현재 날씨: 맑음, 22°C"
```

### 수정: `tools/__init__.py` — 레지스트리 업데이트

```python
from tools.weather import weather_tool

TOOL_REGISTRY: dict = {
    "weather": weather_tool,
}
```

### 수정: `prompts/templates.py`

```python
SYSTEM_PROMPT = """당신은 날씨 정보를 제공하는 AI 봇입니다.
사용자가 위치를 알려주면 해당 지역의 날씨를 조회합니다."""
```

## 핵심 검증 항목

- [ ] `scaffolding/` 복사 후 전체 7개 레이어 존재
- [ ] 날씨 도구가 TOOL_REGISTRY에 등록
- [ ] `graphs/main.py`에서 `create_graph()` 호출 성공
- [ ] 의존성 방향 위반 없음
