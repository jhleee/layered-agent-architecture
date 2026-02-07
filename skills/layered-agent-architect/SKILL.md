---
name: layered-agent-architect
description: >
  Use when building or extending LangGraph agent systems with layered
  architecture, creating StateGraph projects, scaffolding 7-layer structures
  (core, memory, prompts, tools, nodes, graphs, interfaces, config), adding
  tools to registry, creating subgraphs, generating nodes by role type
  (reasoning, execution, routing), managing prompt versions, or running
  dependency lint.
---

# LangGraph 7-Layer Architect

이 스킬은 LangGraph 기반 에이전트 시스템의 7-레이어 아키텍처를 구축·확장할 때 사용한다.

## 사용 규칙

1. **작업 전 반드시** `assets/architecture-rules.md`를 먼저 읽는다
2. **해당 reference만** 온디맨드로 로드한다 (전체 로드 금지)
3. **의존성 방향을 준수**한다 — 상위 → 하위만 import 허용
4. **검증을 수행**한다 — 각 reference의 검증 체크리스트를 완료한다
5. **스케폴딩은 `scaffolding/` 디렉토리를 복사**한다 — 코드 생성 대신 복사 후 수정

## 의도 → 레퍼런스 라우팅

| 사용자 의도 | 참조 파일 | 설명 |
|------------|----------|------|
| 프로젝트 생성, 스케폴딩, 초기화 | `references/01-scaffold.md` | scaffolding/ 복사 + 커스터마이즈 |
| 도구 추가, tool 생성 | `references/02-tool-creator.md` | @tool + 레지스트리 등록 |
| 서브그래프 추가, 멀티에이전트 | `references/03-subgraph-creator.md` | 부분 State + 팩토리 패턴 |
| 노드 추가, reasoning/execution/routing | `references/04-node-creator.md` | 역할별 코드 템플릿 |
| 프롬프트 버전, A/B 테스트 | `references/05-prompt-versioning.md` | 버전 관리 + builder 분기 |
| 문서 생성, README, 다이어그램 | `references/06-docs-generator.md` | Mermaid + README 템플릿 |
| 의존성 검증, lint, 규칙 검사 | `references/07-dependency-lint.md` | AST 기반 import 분석 |

## 빠른 참조

### 디렉토리 구조

```
src/
├── core/          # State, Schema, Model Factory
├── memory/        # Checkpointer, Store
├── prompts/       # Templates, Builder
├── tools/         # Registry, 개별 도구
├── nodes/         # reasoning, execution, routing
├── graphs/        # main, builder, 서브그래프
├── interfaces/    # API (FastAPI), Streaming (SSE)
├── config/        # settings.py, agents.yaml
└── main.py        # 진입점
```

### 의존성 흐름

```
main.py
  └→ interfaces/
       └→ graphs/
            ├→ nodes/
            │    ├→ prompts/
            │    ├→ tools/
            │    └→ core/      ← 최하위
            ├→ memory/
            └→ config/         ← 수평 참조 (어디서든 import 가능)
```
