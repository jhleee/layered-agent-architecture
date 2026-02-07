# 예시 1: Phase 1 프로젝트 스케폴딩

## 사용자 프롬프트

> "langgraph로 날씨 봇 만들어줘"

## 기대 동작

1. `references/01-scaffold.md` 참조
2. Phase 1 (기본값) 선택
3. 다음 구조 생성:

```
weather_bot/
├── core/
│   ├── __init__.py
│   ├── state.py           # AgentState 정의
│   └── schemas.py         # AgentRequest, AgentResponse
├── prompts/
│   ├── __init__.py
│   └── templates.py       # SYSTEM_PROMPT (날씨 봇 맞춤)
├── tools/
│   ├── __init__.py        # TOOL_REGISTRY + get_tools()
│   └── weather.py         # @tool weather_tool
├── nodes/
│   ├── __init__.py
│   ├── reasoning.py       # think 노드
│   └── routing.py         # should_continue
├── graphs/
│   ├── __init__.py
│   └── main.py            # 메인 그래프
└── main.py                # 진입점
```

## 핵심 검증 항목

- [ ] 모든 디렉토리에 `__init__.py` 존재
- [ ] `tools/__init__.py`에 weather_tool이 TOOL_REGISTRY에 등록
- [ ] memory/, interfaces/, config/ 참조 없음 (Phase 1)
- [ ] 의존성 lint 통과 (위반 0)
