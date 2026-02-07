# 01 — 프로젝트 스케폴딩

> 작업 전 `assets/architecture-rules.md`를 먼저 읽는다.

---

## 절차

### Step 1 — scaffolding 복사

이 스킬의 `scaffolding/` 디렉토리를 프로젝트에 복사한다.
7개 레이어, ~18개 파일이 한번에 생성된다.

```bash
cp -r <이_스킬_경로>/scaffolding/ <프로젝트_루트>/src/
```

### Step 2 — 프로젝트 맞춤 수정

| 파일 | 수정 내용 |
|------|----------|
| `core/state.py` | AgentState 필드를 프로젝트에 맞게 추가/수정 |
| `core/schemas.py` | 요청/응답 스키마 수정 |
| `prompts/templates.py` | 시스템 프롬프트 내용 수정 |
| `tools/search.py` | 프로젝트에 필요한 도구로 교체 |
| `tools/__init__.py` | TOOL_REGISTRY에 도구 등록/제거 |
| `config/settings.py` | 환경 변수 추가 |
| `config/agents.yaml` | 에이전트 구성 수정 |
| `main.py` | 진입점 로직 수정 |

### Step 3 — 검증

- [ ] 모든 레이어 디렉토리에 `__init__.py` 존재
- [ ] `layers/` 같은 래퍼 디렉토리 없음
- [ ] `tools/__init__.py`에 TOOL_REGISTRY 정의됨
- [ ] `graphs/main.py`에서 `create_graph()` 호출 가능
- [ ] 의존성 방향 준수 (lint 스크립트로 확인)

---

## 생성되는 구조

```
src/
├── core/           # State, Schema, Model Factory
│   ├── state.py
│   ├── schemas.py
│   └── models.py
├── memory/         # Checkpointer, Store
│   ├── checkpointer.py
│   └── store.py
├── prompts/        # Templates, Builder
│   ├── templates.py
│   └── builder.py
├── tools/          # Registry, Base, 개별 도구
│   ├── __init__.py (TOOL_REGISTRY)
│   ├── base.py
│   └── search.py
├── nodes/          # reasoning, execution, routing
│   ├── reasoning.py
│   ├── execution.py
│   └── routing.py
├── graphs/         # main, builder
│   ├── builder.py
│   └── main.py
├── interfaces/     # API (FastAPI), Streaming (SSE)
│   ├── api.py
│   └── stream.py
├── config/         # settings.py, agents.yaml
│   ├── settings.py
│   └── agents.yaml
└── main.py         # 진입점
```
