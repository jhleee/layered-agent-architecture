# Architecture Rules — LangGraph 7-Layer Agent System

> 이 파일은 모든 reference 모듈이 공유하는 핵심 규칙을 정의한다.
> reference 파일은 작업 전 이 파일을 먼저 읽어야 한다.

---

## 1. 7대 설계 원칙 요약

| # | 원칙 | 핵심 규칙 |
|---|------|----------|
| 1 | 평면 우선 (Flat-First) | `layers/`, `modules/` 같은 메타 래퍼 폴더 금지. 네스팅 깊이 최대 1단계 |
| 2 | 역할별 파일 분리 | 파일명만으로 역할 유추 가능. 1파일 = 1관심사 |
| 3 | 선택적 레이어 | 레이어가 없어도 시스템 동작. 필요 시 점진 추가 |
| 4 | 팩토리 추상화 | 직접 인스턴스 생성 대신 팩토리 함수 사용 (`get_model()`, `get_tools()`) |
| 5 | 단방향 의존 | 상위 → 하위만 import 허용. 역방향/순환 금지 |
| 6 | 설정 외부화 | 하드코딩 값은 `config/`로 추출 (Phase 3) |
| 7 | 서브그래프 독립성 | 1 서브그래프 = 1 파일. 단독 compile·테스트 가능 |

---

## 2. 레이어 의존성 매트릭스

```
허용 방향 (→ import 가능):

main.py → interfaces/ → graphs/ → nodes/ → prompts/, tools/, core/
                                          → memory/, config/
```

| 레이어 | import 가능 대상 | import 금지 대상 |
|--------|----------------|-----------------|
| `core/` | 없음 (자기 완결, 외부 라이브러리만) | 모든 다른 레이어 |
| `memory/` | `core/` | nodes/, graphs/, interfaces/, tools/, prompts/ |
| `prompts/` | `core/` | nodes/, graphs/, interfaces/, tools/, memory/ |
| `tools/` | `core/` | nodes/, graphs/, interfaces/, prompts/, memory/ |
| `nodes/` | `core/`, `prompts/`, `tools/` | graphs/, interfaces/, memory/ |
| `graphs/` | `nodes/`, `memory/`, `config/`, `core/` | interfaces/ |
| `interfaces/` | `graphs/`, `core/` | nodes/, tools/, prompts/ (직접 참조 금지) |
| `config/` | 외부 라이브러리만 (수평 참조 허용 — 여러 레이어에서 config/ 참조 가능) | 없음 |

**특수 규칙:**
- `config/`는 수평 참조 허용: 어떤 레이어든 `config/`를 import할 수 있다
- `core/`에서 다른 레이어 import 시 → 공통 부분을 `core/`로 추출하여 순환 해소

---

## 3. Phase별 필수 파일

### Phase 1 (~8 파일, 최소 시작)

```
agent_system/
├── core/
│   ├── __init__.py
│   ├── state.py           # AgentState + Reducer
│   └── schemas.py         # Pydantic 요청/응답
├── prompts/
│   ├── __init__.py
│   └── templates.py       # 프롬프트 상수
├── tools/
│   ├── __init__.py        # TOOL_REGISTRY + get_tools()
│   └── search.py          # 최초 도구 1개
├── nodes/
│   ├── __init__.py
│   ├── reasoning.py       # think 노드
│   └── routing.py         # should_continue
├── graphs/
│   ├── __init__.py
│   └── main.py            # 메인 그래프
└── main.py                # 진입점
```

### Phase 2 (~14 파일, 기능 확장)

Phase 1에 추가:
- `core/models.py` — Model Factory
- `tools/base.py` — 도구 베이스 클래스
- `prompts/builder.py` — 동적 프롬프트 빌더
- `nodes/execution.py` — 실행 노드
- `graphs/<subgraph>.py` — 서브그래프 파일
- `graphs/builder.py` — 그래프 빌더 유틸

### Phase 3 (~18 파일, 프로덕션 완비)

Phase 2에 추가:
- `config/settings.py` + `config/agents.yaml`
- `memory/checkpointer.py` + `memory/store.py`
- `interfaces/api.py` + `interfaces/stream.py`

---

## 4. 노드 역할 경계

| 파일 | 역할 | LLM 호출 | 도구 실행 | State 수정 |
|------|------|---------|---------|-----------|
| `reasoning.py` | 추론, 계획 수립 | O | X | messages, current_plan, iteration |
| `execution.py` | 도구 실행, 결과 처리 | X | O | messages, context |
| `routing.py` | 분기 결정 (순수 함수) | X | X | 없음 (문자열 반환만) |

### 경계 위반 안티패턴

| 위반 | 설명 | 위험 |
|------|------|------|
| reasoning에서 도구 직접 호출 | `think()` 안에서 `tool.invoke()` | 에러 핸들링 누락 |
| execution에서 라우팅 판단 | `execute_tools()` 안에서 다음 노드 결정 | 흐름 분산 |
| routing에서 LLM 호출 | `should_continue()`에서 LLM 분기 판단 | 비결정적, 비용 증가 |

---

## 5. 네이밍 규칙

| 대상 | 규칙 | 예시 |
|------|------|------|
| 디렉토리 | 소문자, 복수형 | `tools/`, `nodes/`, `graphs/` |
| 파일 | 소문자, snake_case | `reasoning.py`, `check_pointer.py` |
| 클래스 | PascalCase | `AgentState`, `SearchTool` |
| 함수 | snake_case | `get_model()`, `should_continue()` |
| 상수 | UPPER_SNAKE_CASE | `TOOL_REGISTRY`, `SYSTEM_PROMPT` |

---

## 6. 구조 제약

- **1 폴더 = 1 레이어**: `layers/` 같은 래퍼 디렉토리 금지
- **1 파일 = 1 역할**: 하나의 파일에 여러 관심사 혼합 금지
- **네스팅 최대 1**: `agent_system/<layer>/<file>.py` 이상 불가
- **`__init__.py`는 내보내기 전용**: 로직 금지 (`tools/__init__.py`의 레지스트리 제외)
- **서브그래프 1개 = 파일 1개**: `graphs/researcher.py`, `graphs/writer.py`
- **도구 1개 = 파일 1개**: 관련 도구 2-3개는 같은 파일 허용
- **서브그래프 간 직접 통신 금지**: 반드시 메인 그래프를 경유

---

## 7. 무한 루프 방지

에이전트 그래프에서 다중 안전장치를 적용한다:

| 안전장치 | 수준 | 동작 |
|---------|------|------|
| `iteration` 카운터 (routing.py) | 비즈니스 로직 | 의미 있는 반복 횟수 제한 (기본 5회) |
| `recursion_limit` (그래프 실행 시) | 프레임워크 | 절대 상한선, 초과 시 예외 발생 |
