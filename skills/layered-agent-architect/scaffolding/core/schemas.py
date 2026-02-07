from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """에이전트 요청 스키마."""
    query: str = Field(..., min_length=1)
    session_id: str | None = None


class AgentResponse(BaseModel):
    """에이전트 응답 스키마."""
    answer: str
    sources: list[str] = []
