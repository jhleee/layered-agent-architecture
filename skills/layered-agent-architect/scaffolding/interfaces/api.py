from fastapi import FastAPI
from core.schemas import AgentRequest, AgentResponse
from graphs.main import create_graph
from memory.checkpointer import get_checkpointer

app = FastAPI()
graph = create_graph(checkpointer=get_checkpointer())


@app.post("/chat", response_model=AgentResponse)
async def chat(request: AgentRequest):
    """채팅 엔드포인트."""
    config = {}
    if request.session_id:
        config["configurable"] = {"thread_id": request.session_id}

    result = await graph.ainvoke(
        {
            "messages": [{"role": "user", "content": request.query}],
            "current_plan": "",
            "iteration": 0,
            "final_answer": None,
        },
        config=config,
    )
    return AgentResponse(
        answer=result["messages"][-1].content,
        sources=[],
    )
