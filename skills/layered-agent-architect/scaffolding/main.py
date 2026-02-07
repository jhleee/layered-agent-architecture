import asyncio
from graphs.main import create_graph
from memory.checkpointer import get_checkpointer


async def main():
    graph = create_graph(checkpointer=get_checkpointer())
    result = await graph.ainvoke({
        "messages": [{"role": "user", "content": "안녕하세요"}],
        "current_plan": "",
        "iteration": 0,
        "final_answer": None,
    })
    print(result.get("final_answer", result["messages"][-1].content))


if __name__ == "__main__":
    asyncio.run(main())
