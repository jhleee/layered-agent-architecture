import json
from fastapi.responses import StreamingResponse


async def stream_response(graph, inputs: dict, config: dict | None = None):
    """SSE 스트리밍 응답을 생성한다."""
    async def event_generator():
        async for event in graph.astream_events(inputs, config=config or {}, version="v2"):
            yield f"data: {json.dumps(event, default=str)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
