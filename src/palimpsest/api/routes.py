import time

from fastapi import APIRouter, Request

from palimpsest.api.schemas import AskRequest, AskResponse

router = APIRouter()


@router.post("/ask")
def ask(request: Request, ask: AskRequest):
    messages = [{"role": "user", "content": ask.question}]

    start = time.monotonic()
    result = request.app.state.agent.invoke({"messages": messages, "iterations": 0})
    latency_ms = int((time.monotonic() - start) * 1000)

    last_message = result["messages"][-1]

    return AskResponse(
        answer=last_message["content"],
        citation_problems=result.get("citation_problems"),
        tool_calls=[c for m in result["messages"] for c in (m.get("tool_calls") or [])],
        latency_ms=latency_ms,
    )
