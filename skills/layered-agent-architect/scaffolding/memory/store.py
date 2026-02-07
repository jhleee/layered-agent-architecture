from langgraph.store.memory import InMemoryStore


def get_store():
    """환경에 따라 적절한 저장소를 반환한다."""
    return InMemoryStore()
