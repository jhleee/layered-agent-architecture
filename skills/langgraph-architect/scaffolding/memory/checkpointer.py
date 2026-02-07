from langgraph.checkpoint.memory import MemorySaver


def get_checkpointer():
    """환경에 따라 적절한 체크포인터를 반환한다."""
    return MemorySaver()
