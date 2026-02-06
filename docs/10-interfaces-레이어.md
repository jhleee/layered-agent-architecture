# 제10장 Interfaces 레이어

> [← 이전: 제9장 Graphs 레이어](./09-graphs-레이어.md) | [목차](./index.md) | [다음: 제11장 Config 레이어 →](./11-config-레이어.md)

---

## 이 장의 파일 범위

```
interfaces/
├── __init__.py
├── api.py       ← 10.1
└── stream.py    ← 10.2
```

`interfaces/` 레이어는 **그래프를 외부에 노출하는 책임**을 담당한다. 그래프 로직과 서빙(serving) 로직을 분리하여, 배포 방식이 변해도 그래프 코드는 수정하지 않아도 된다.

---

## 핵심 설계 결정: 왜 분리인가

실용적 접근에서는 `app.py` 하나에 그래프 조립과 API 서빙을 통합했다. 통합 아키텍처에서는 이를 분리한다.

### 분리 근거

| 관점 | 통합 (app.py) | 분리 (interfaces/) |
|---|---|---|
| **관심사** | 그래프 + API가 혼재 | 그래프 로직 ≠ 서빙 로직 |
| **교체 가능성** | CLI에서 API로 변경 시 전체 수정 | 인터페이스 파일만 교체 |
| **테스트** | API 테스트에 그래프 초기화 필수 | 그래프와 API를 독립 테스트 |
| **배포** | 단일 배포 방식 | CLI, REST, WebSocket 등 선택 가능 |

### 엔터프라이즈 접근의 formatter.py 처리

엔터프라이즈 접근에서는 응답 포매팅을 `formatter.py`로 분리했으나, 통합 아키텍처에서는 **`stream.py`에 흡수**한다. 포매팅은 스트리밍 응답 생성의 일부이므로 별도 파일로 분리할 정당성이 부족하다.

---

## 10.1 REST API 설계 (api.py)

### 10.1.1 FastAPI 엔드포인트 구조

```python
# interfaces/api.py

from fastapi import FastAPI, HTTPException
from core.schemas import AgentRequest, AgentResponse
from graphs.main import create_graph

app = FastAPI(
    title="Agent System API",
    description="LangGraph 기반 에이전트 시스템 REST API",
    version="1.0.0",
)

# 그래프 인스턴스 (앱 시작 시 1회 생성)
_graph = None


def get_graph():
    """그래프 인스턴스를 싱글턴으로 관리한다."""
    global _graph
    if _graph is None:
        try:
            from memory.checkpointer import get_checkpointer
            from memory.store import get_store
            _graph = create_graph(
                checkpointer=get_checkpointer(),
                store=get_store(),
            )
        except ImportError:
            # memory/ 레이어가 없는 Phase 1
            _graph = create_graph()
    return _graph


@app.post("/chat", response_model=AgentResponse)
async def chat(request: AgentRequest):
    """에이전트와 대화한다.

    Args:
        request: 사용자 요청 (message, thread_id 등)

    Returns:
        에이전트 응답 (answer, thread_id, iterations 등)
    """
    graph = get_graph()

    # 실행 설정
    config = {}
    if request.thread_id:
        config["configurable"] = {"thread_id": request.thread_id}

    try:
        # 그래프 실행
        result = await graph.ainvoke(
            {
                "messages": [{"role": "user", "content": request.message}],
                "context": [],
                "current_plan": "",
                "iteration": 0,
                "final_answer": None,
            },
            config=config,
        )

        return AgentResponse(
            answer=result.get("final_answer", "응답을 생성하지 못했습니다."),
            thread_id=request.thread_id or "default",
            iterations=result.get("iteration", 0),
            tools_used=[],  # 도구 사용 이력 추출 로직
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """서버 상태 확인 엔드포인트"""
    return {"status": "healthy"}
```

### 10.1.2 엔드포인트 설계 원칙

| 원칙 | 설명 |
|---|---|
| **스키마 활용** | `core/schemas.py`의 Pydantic 모델을 요청/응답에 사용 |
| **그래프 싱글턴** | 그래프 인스턴스를 앱 수준에서 1회만 생성 |
| **에러 전파** | 그래프 실행 에러를 HTTP 상태 코드로 매핑 |
| **설정 분리** | 실행 설정(thread_id 등)은 LangGraph의 config 딕셔너리로 전달 |

### 10.1.3 에러 핸들링

```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """전역 에러 핸들러"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
        },
    )
```

---

## 10.2 스트리밍 핸들러 (stream.py)

### 10.2.1 SSE (Server-Sent Events) 구현

스트리밍은 에이전트의 응답을 **실시간으로** 클라이언트에 전달한다. LLM의 토큰 생성을 기다리지 않고 즉시 표시할 수 있어 UX를 크게 개선한다.

```python
# interfaces/stream.py

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from core.schemas import AgentRequest
from graphs.main import create_graph
import json


async def stream_agent_response(request: AgentRequest):
    """에이전트 응답을 SSE로 스트리밍한다.

    LangGraph의 astream_events를 활용하여
    토큰 단위로 클라이언트에 전송한다.
    """
    graph = create_graph()

    config = {}
    if request.thread_id:
        config["configurable"] = {"thread_id": request.thread_id}

    initial_state = {
        "messages": [{"role": "user", "content": request.message}],
        "context": [],
        "current_plan": "",
        "iteration": 0,
        "final_answer": None,
    }

    async for event in graph.astream_events(initial_state, config=config, version="v2"):
        event_type = event["event"]

        if event_type == "on_chat_model_stream":
            # LLM 토큰 스트리밍
            chunk = event["data"]["chunk"]
            if chunk.content:
                yield format_sse_event("token", {"content": chunk.content})

        elif event_type == "on_tool_start":
            # 도구 실행 시작 알림
            tool_name = event["name"]
            yield format_sse_event("tool_start", {"tool": tool_name})

        elif event_type == "on_tool_end":
            # 도구 실행 완료 알림
            tool_name = event["name"]
            yield format_sse_event("tool_end", {"tool": tool_name})

    # 스트리밍 종료
    yield format_sse_event("done", {})


def format_sse_event(event_type: str, data: dict) -> str:
    """SSE 프로토콜에 맞게 이벤트를 포맷팅한다.

    엔터프라이즈 접근의 formatter.py 역할을 여기서 수행한다.
    """
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
```

### 10.2.2 스트리밍 엔드포인트 등록

```python
# interfaces/api.py 에 스트리밍 엔드포인트 추가

from interfaces.stream import stream_agent_response

@app.post("/chat/stream")
async def chat_stream(request: AgentRequest):
    """에이전트 응답을 실시간 스트리밍한다."""
    return StreamingResponse(
        stream_agent_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
```

### 10.2.3 이벤트 유형

스트리밍 중 클라이언트가 수신하는 이벤트 유형:

| 이벤트 | 설명 | 데이터 |
|---|---|---|
| `token` | LLM이 생성한 토큰 | `{"content": "..."}` |
| `tool_start` | 도구 실행 시작 | `{"tool": "search"}` |
| `tool_end` | 도구 실행 완료 | `{"tool": "search"}` |
| `done` | 스트리밍 종료 | `{}` |

---

## 10.3 배포 시나리오별 인터페이스 구성

인터페이스 레이어의 교체 가능성을 활용하여, 배포 시나리오에 따라 적절한 인터페이스를 선택한다:

| 시나리오 | 사용 인터페이스 | 설명 |
|---|---|---|
| **로컬 개발** | `main.py` 직접 실행 | `interfaces/` 없이도 동작 |
| **API 서버** | `api.py` (FastAPI) | REST 엔드포인트 제공 |
| **실시간 채팅** | `stream.py` (SSE) | 토큰 단위 스트리밍 |
| **LangServe** | `api.py` 확장 | LangServe의 `add_routes` 활용 |

### 로컬 개발 시 (interfaces/ 없이)

```python
# main.py (실행 진입점)
import asyncio
from graphs.main import create_graph

async def main():
    graph = create_graph()
    result = await graph.ainvoke({
        "messages": [{"role": "user", "content": "안녕하세요"}],
        "context": [],
        "current_plan": "",
        "iteration": 0,
        "final_answer": None,
    })
    print(result["final_answer"])

if __name__ == "__main__":
    asyncio.run(main())
```

### API 서버 배포 시

```bash
uvicorn interfaces.api:app --host 0.0.0.0 --port 8000
```

---

## interfaces/ 레이어 정리

| 파일 | 역할 | 선택 사항 |
|---|---|---|
| `api.py` | REST API 엔드포인트 (FastAPI) | Phase 3에서 도입 |
| `stream.py` | SSE 스트리밍 핸들러 + 이벤트 포매팅 | 실시간 응답 필요 시 |

인터페이스 레이어의 핵심 가치는 **그래프 로직을 어떤 방식으로든 노출할 수 있는 유연성**이다. 그래프 코드를 한 줄도 수정하지 않고 CLI에서 REST API, 스트리밍, WebSocket 등으로 서빙 방식을 전환할 수 있다.

---

> [← 이전: 제9장 Graphs 레이어](./09-graphs-레이어.md) | [목차](./index.md) | [다음: 제11장 Config 레이어 →](./11-config-레이어.md)
