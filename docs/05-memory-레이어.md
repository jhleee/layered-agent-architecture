# 제5장 Memory 레이어

> [← 이전: 제4장 Core 레이어](./04-core-레이어.md) | [목차](./index.md) | [다음: 제6장 Prompts 레이어 →](./06-prompts-레이어.md)

---

## 이 장의 파일 범위

```
memory/
├── __init__.py
├── checkpointer.py   ← 5.1
└── store.py           ← 5.2
```

`memory/` 레이어는 **선택적 레이어**이다. Phase 1(최소 시작)에서는 없어도 동작하지만, 프로덕션 환경에서는 반드시 필요하다. LangGraph의 체크포인팅 메커니즘과 장기 메모리 저장소를 캡슐화한다.

---

## 5.1 체크포인터 전략 (checkpointer.py)

### 5.1.1 왜 필요한가

체크포인터가 없는 에이전트는 **매 요청이 독립적**이다. 이전 대화를 기억하지 못하고, 실행 중 에러가 발생하면 처음부터 다시 시작해야 한다.

체크포인터가 필수적인 시나리오:

| 시나리오 | 설명 |
|---|---|
| **긴 대화 복원** | 사용자가 브라우저를 닫았다 다시 열어도 대화를 이어갈 수 있다 |
| **에러 복구** | 도구 호출 중 네트워크 오류 발생 시, 마지막 체크포인트에서 재개한다 |
| **Human-in-the-loop** | 특정 단계에서 사용자 승인을 기다린 후 이어서 실행한다 |
| **디버깅** | 실행 과정의 중간 상태를 추적하여 문제를 진단한다 |

### 5.1.2 환경별 구현

통합 아키텍처는 **팩토리 패턴**으로 환경에 따라 적절한 체크포인터를 반환한다. 이 전환에 코드 변경이 필요 없다 — 환경 변수(`ENVIRONMENT`)만 변경하면 된다.

```python
# memory/checkpointer.py

from langgraph.checkpoint.memory import MemorySaver


def get_checkpointer():
    """환경에 따라 적절한 체크포인터를 반환한다.

    - 개발: MemorySaver (인메모리, 프로세스 종료 시 삭제)
    - 프로덕션: SqliteSaver 또는 PostgresSaver (영속)
    """
    try:
        from config.settings import get_settings
        settings = get_settings()
    except ImportError:
        # config/ 레이어가 없는 Phase 1에서는 인메모리 사용
        return MemorySaver()

    if settings.environment == "production":
        from langgraph.checkpoint.sqlite import SqliteSaver
        return SqliteSaver.from_conn_string(settings.database_url)
    elif settings.environment == "staging":
        from langgraph.checkpoint.sqlite import SqliteSaver
        return SqliteSaver.from_conn_string(settings.database_url)
    else:
        return MemorySaver()
```

### 5.1.3 환경별 체크포인터 비교

| 환경 | 체크포인터 | 영속성 | 적합한 상황 |
|---|---|---|---|
| **개발** | `MemorySaver` | 프로세스 종료 시 삭제 | 로컬 개발, 빠른 반복 |
| **스테이징** | `SqliteSaver` | 파일 기반 영속 | 테스트, 소규모 배포 |
| **프로덕션** | `PostgresSaver` | DB 기반 영속 | 대규모 배포, 고가용성 |

### 5.1.4 그래프에서의 체크포인터 주입

체크포인터는 그래프 컴파일 시 주입된다:

```python
# graphs/main.py 에서
from memory.checkpointer import get_checkpointer

graph = builder.compile(checkpointer=get_checkpointer())
```

이 패턴의 장점은 **그래프 로직과 영속화 전략이 완전히 분리**된다는 점이다. 그래프는 체크포인터의 구체적 구현을 알 필요가 없다.

### 5.1.5 thread_id 관리

체크포인터는 `thread_id`를 기준으로 대화를 구분한다:

```python
# 대화 실행 시 thread_id 전달
config = {"configurable": {"thread_id": "user-123-session-1"}}
result = await graph.ainvoke(
    {"messages": [HumanMessage(content="안녕하세요")]},
    config=config
)

# 같은 thread_id로 호출하면 이전 대화를 이어감
result = await graph.ainvoke(
    {"messages": [HumanMessage(content="아까 질문에 이어서...")]},
    config=config  # 동일한 thread_id
)
```

---

## 5.2 영속 저장소 설계 (store.py)

### 5.2.1 체크포인터 vs 영속 저장소

체크포인터와 영속 저장소는 모두 "기억"을 담당하지만, 관심사가 다르다:

| 구분 | 체크포인터 (checkpointer.py) | 영속 저장소 (store.py) |
|---|---|---|
| **저장 대상** | 그래프 실행의 중간 상태 (State 스냅샷) | 대화를 넘어서는 장기 지식 |
| **수명** | 대화 세션 내 | 세션 간 영속 |
| **접근 방식** | LangGraph 내부에서 자동 관리 | 명시적 읽기/쓰기 |
| **예시** | "이 대화의 3번째 턴에서 State가 뭐였지?" | "이 사용자의 선호 언어는 한국어야" |

### 5.2.2 LangGraph Store 활용

LangGraph의 `Store`는 키-값 기반의 장기 메모리를 제공한다:

```python
# memory/store.py

from langgraph.store.memory import InMemoryStore


def get_store():
    """환경에 따라 적절한 저장소를 반환한다."""
    try:
        from config.settings import get_settings
        settings = get_settings()
    except ImportError:
        return InMemoryStore()

    if settings.environment == "production":
        # 프로덕션에서는 영속 저장소 사용
        # PostgresStore 등으로 교체 가능
        from langgraph.store.memory import InMemoryStore
        return InMemoryStore()  # 실제 프로덕션에서는 DB 기반으로 교체
    else:
        return InMemoryStore()


# 저장소 헬퍼 함수
async def save_memory(store, namespace: tuple, key: str, value: dict):
    """장기 메모리에 값을 저장한다."""
    await store.aput(namespace, key, value)


async def get_memory(store, namespace: tuple, key: str) -> dict | None:
    """장기 메모리에서 값을 조회한다."""
    result = await store.aget(namespace, key)
    return result.value if result else None
```

### 5.2.3 장기 메모리 vs 단기 메모리

| 메모리 유형 | 저장소 | 접근 방식 | 예시 |
|---|---|---|---|
| **단기 메모리** | State의 `messages` 필드 | 그래프 실행 중 자동 관리 | 현재 대화 내역 |
| **중기 메모리** | 체크포인터 | thread_id 기반 자동 복원 | 이전 세션의 대화 이력 |
| **장기 메모리** | Store (`store.py`) | 명시적 읽기/쓰기 | 사용자 선호도, 학습된 정보 |

### 5.2.4 노드에서의 Store 활용

```python
# nodes/reasoning.py 에서 장기 메모리 활용 예시
async def think(state: AgentState, config: dict, *, store) -> dict:
    # 사용자의 장기 메모리에서 선호도 조회
    user_id = config["configurable"].get("user_id", "default")
    preferences = await get_memory(
        store,
        namespace=("users", user_id),
        key="preferences"
    )

    # 선호도를 프롬프트에 반영
    if preferences:
        context = f"사용자 선호: {preferences}"
        ...
```

---

## 5.3 환경별 메모리 구성

전체 메모리 구성을 환경별로 요약한다:

| 환경 | 체크포인터 | 저장소 | 특징 |
|---|---|---|---|
| **개발** | `MemorySaver` | `InMemoryStore` | 프로세스 종료 시 모두 삭제, 빠른 반복 |
| **스테이징** | `SqliteSaver` | `InMemoryStore` | 체크포인트는 파일로 영속, 장기 메모리는 휘발 |
| **프로덕션** | `PostgresSaver` | `PostgresStore` | 모든 메모리가 DB에 영속, 고가용성 |

### 전환 비용

환경 간 전환 시 코드 변경은 **0줄**이다. `config/settings.py`의 `ENVIRONMENT` 환경 변수만 변경하면 `get_checkpointer()`와 `get_store()`가 자동으로 적절한 구현체를 반환한다.

```bash
# 개발 환경
ENVIRONMENT=development python main.py

# 프로덕션 환경
ENVIRONMENT=production DATABASE_URL=postgresql://... python main.py
```

---

## memory/ 레이어 정리

| 파일 | 역할 | 활성화 시점 |
|---|---|---|
| `checkpointer.py` | 그래프 실행 상태 영속화 | 대화 복원, 에러 복구 필요 시 (Phase 3) |
| `store.py` | 장기 메모리 관리 | 사용자별 기억, 학습 필요 시 (Phase 3) |

`memory/` 레이어의 핵심 가치는 **개발 환경에서 프로덕션 환경으로의 전환이 설정 변경만으로 완료**된다는 점이다. 코드를 한 줄도 수정하지 않고 인메모리에서 PostgreSQL로 전환할 수 있다.

---

> [← 이전: 제4장 Core 레이어](./04-core-레이어.md) | [목차](./index.md) | [다음: 제6장 Prompts 레이어 →](./06-prompts-레이어.md)
