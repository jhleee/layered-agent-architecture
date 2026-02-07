from functools import lru_cache
from langchain_openai import ChatOpenAI


@lru_cache
def get_model(model_name: str = "gpt-4o", temperature: float = 0):
    """모델 팩토리: 동일 파라미터면 캐시된 인스턴스를 반환한다."""
    return ChatOpenAI(model=model_name, temperature=temperature)


reasoning_model = lambda: get_model("gpt-4o", 0)
fast_model = lambda: get_model("gpt-4o-mini", 0)
creative_model = lambda: get_model("gpt-4o", 0.7)
