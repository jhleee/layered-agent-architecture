# LangGraph 에이전트 시스템 통합 아키텍처

> **직관성과 확장성의 균형: 프로토타입에서 프로덕션까지 하나의 구조로**

---

## 개요

본 프로젝트는 LangGraph 기반 에이전트 시스템을 구축할 때 반복적으로 직면하는 아키텍처 딜레마 — "빠르게 만들 수 있지만 확장이 어려운 구조"와 "확장 가능하지만 시작이 무거운 구조" — 를 해소하기 위한 **통합 아키텍처**를 제시한다.

7개 레이어, 약 18개 파일로 구성된 이 아키텍처는 최소 8개 파일로 동작하는 프로토타입에서 시작하여, 코드 재설계 없이 프로덕션 수준의 시스템으로 점진 확장할 수 있다.

---

## 아키텍처 한눈에 보기

```
agent_system/
├── core/           # 기반 레이어 — State, Schema, Model Factory
│   ├── state.py         # State 정의 + Reducer
│   ├── schemas.py       # Pydantic I/O 모델
│   └── models.py        # LLM 설정 + 팩토리
│
├── memory/         # 메모리 레이어 — 상태 영속화
│   ├── checkpointer.py  # 체크포인터 전략
│   └── store.py         # 영속 저장소
│
├── prompts/        # 프롬프트 레이어 — 템플릿 관리
│   ├── templates.py     # 프롬프트 템플릿
│   └── builder.py       # 동적 조합 빌더
│
├── tools/          # 도구 레이어 — 외부 도구 정의
│   ├── __init__.py      # 레지스트리 + 내보내기
│   ├── base.py          # 도구 베이스 클래스
│   └── <tool>.py        # 개별 도구 구현
│
├── nodes/          # 노드 레이어 — 처리 로직
│   ├── reasoning.py     # 추론/사고 노드
│   ├── execution.py     # 도구 실행 노드
│   └── routing.py       # 조건부 분기 로직
│
├── graphs/         # 그래프 레이어 — 워크플로 조립
│   ├── builder.py       # 그래프 빌더 유틸
│   ├── <subgraph>.py    # 서브그래프 (독립 파일)
│   └── main.py          # 메인 그래프 조립
│
├── interfaces/     # 인터페이스 레이어 — 외부 노출
│   ├── api.py           # REST 엔드포인트
│   └── stream.py        # SSE 스트리밍 핸들러
│
├── config/         # 설정 — 환경 및 에이전트 구성
│   ├── settings.py      # 환경 변수 (Pydantic Settings)
│   └── agents.yaml      # 선언적 에이전트 구성
│
└── main.py         # 실행 진입점
```

---

## 7대 설계 원칙

| # | 원칙 | 적용 |
|---|------|------|
| 1 | **평면 우선 구조** (Flat-First) | `layers/` 래퍼 없이 폴더 = 레이어 |
| 2 | **역할별 파일 분리** (Role per File) | nodes/ 내 reasoning/execution/routing 각각 파일 |
| 3 | **선택적 레이어** (Optional Layer) | memory/, interfaces/ 등은 빈 껍데기로 시작 가능 |
| 4 | **팩토리로 추상화** (Factory Pattern) | models.py, tool registry로 교체 용이성 확보 |
| 5 | **단방향 의존** (Unidirectional) | core → 상위 방향만 의존, 역방향 금지 |
| 6 | **설정 외부화** (Externalize Config) | 하드코딩 → settings.py / agents.yaml로 추출 |
| 7 | **서브그래프 독립성** (Subgraph Independence) | 각 서브그래프 = 독립 파일, 단독 테스트 가능 |

---

## 점진적 확장 전략

### Phase 1 — 최소 시작 (~8 파일)

```
core/state.py, core/schemas.py
prompts/templates.py
tools/__init__.py, tools/<tool>.py
nodes/reasoning.py, nodes/routing.py
graphs/main.py
```

### Phase 2 — 기능 확장 (~14 파일)

```
+ core/models.py           → 모델 팩토리
+ tools/base.py            → 도구 표준화
+ prompts/builder.py       → 동적 프롬프트
+ nodes/execution.py       → 실행 노드 분리
+ graphs/<subgraph>.py     → 서브그래프
```

### Phase 3 — 프로덕션 전환 (~18 파일)

```
+ memory/checkpointer.py   → 상태 영속화
+ memory/store.py          → 장기 메모리
+ interfaces/api.py        → REST API
+ interfaces/stream.py     → 스트리밍
+ config/settings.py       → 환경 설정
+ config/agents.yaml       → 선언적 구성
```

---

## 레이어 의존성 흐름

```
main.py
  ↓
interfaces/        API, 스트리밍
  ↓
graphs/            그래프 조립
  ↓
├── nodes/         추론, 실행, 라우팅
├── memory/        체크포인터, 스토어
└── config/        설정
  ↓
├── prompts/       템플릿, 빌더
├── tools/         레지스트리, 도구
└── core/          State, Schema, Models ← 최하위 기반
```

> **규칙:** 화살표 방향(하향)으로만 import 허용. 역방향·순환 의존 금지.

---

## 문서 구조

상세 설계 문서는 [`docs/`](./docs/) 디렉토리에 챕터별로 정리되어 있다.

| 장 | 제목 | 핵심 내용 |
|---|------|----------|
| [1장](./docs/01-서론.md) | 서론 | 배경, 목적, 대상 독자, 용어 정의 |
| [2장](./docs/02-설계-원칙.md) | 설계 원칙 | 설계 철학, 7대 원칙, 채택·폐기 기준 |
| [3장](./docs/03-전체-구조.md) | 전체 구조 | 디렉토리 구조, 의존성 흐름, 데이터 흐름 |
| [4장](./docs/04-core-레이어.md) | Core 레이어 | State, Schema, Model Factory |
| [5장](./docs/05-memory-레이어.md) | Memory 레이어 | 체크포인터, 영속 저장소, 환경별 구성 |
| [6장](./docs/06-prompts-레이어.md) | Prompts 레이어 | 템플릿, 동적 빌더, 버전 관리 |
| [7장](./docs/07-tools-레이어.md) | Tools 레이어 | 베이스 클래스, 레지스트리, 확장 전략 |
| [8장](./docs/08-nodes-레이어.md) | Nodes 레이어 | 추론, 실행, 라우팅 노드 |
| [9장](./docs/09-graphs-레이어.md) | Graphs 레이어 | 빌더 유틸, 서브그래프, 메인 그래프 |
| [10장](./docs/10-interfaces-레이어.md) | Interfaces 레이어 | REST API, 스트리밍 핸들러 |
| [11장](./docs/11-config-레이어.md) | Config 레이어 | 환경 변수, 선언적 에이전트 구성 |

---

## Claude Code 플러그인

이 레포지토리는 Claude Code 플러그인으로 배포된다. 설치하면 LangGraph 프로젝트를 스케폴딩하고, 도구/노드/서브그래프를 추가하고, 아키텍처 규칙을 검증하는 스킬을 사용할 수 있다.

### 설치

```bash
/plugin marketplace add jhleee/layered-agent-architecture
/plugin install langgraph-architect
```

### 사용 예시

| 프롬프트 | 동작 |
|---------|------|
| "langgraph로 날씨 봇 만들어줘" | Phase 1 프로젝트 스케폴딩 |
| "weather_tool 추가해줘" | 도구 생성 + 레지스트리 등록 |
| "리서처 서브그래프 추가" | 부분 State + 팩토리 함수 + 메인 그래프 연결 |
| "요약 reasoning 노드 추가" | 역할별 노드 템플릿 적용 |
| "시스템 프롬프트 v2 만들어줘" | 프롬프트 버전 관리 |
| "의존성 규칙 검사해줘" | AST 기반 import lint |
| "Phase 1에서 Phase 2로 확장" | 증분 파일 추가 |

### 설치 범위

```bash
/plugin install langgraph-architect --scope user      # 모든 프로젝트
/plugin install langgraph-architect --scope project   # 현재 프로젝트 (팀 공유)
/plugin install langgraph-architect --scope local     # 로컬만
```

---

## SKILLS (구현 지침)

아키텍처를 기반으로 실제 코드를 생성하기 위한 SKILLS 지침은 [`SKILLS.md`](./SKILLS.md)에 정의되어 있다. 플러그인 설치 후에는 스킬이 자동으로 참조되므로 이 문서를 직접 읽을 필요가 없다.

---

## 문서 정보

- **버전:** 1.0
- **대상 프레임워크:** LangGraph (Python)
- **범위:** 단일 에이전트 ~ 멀티 에이전트 서브그래프 구조
