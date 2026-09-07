from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class AskResponse(BaseModel):
    answer: str
    citation_problems: list[str]
    tool_calls: list[dict]
    latency_ms: int
