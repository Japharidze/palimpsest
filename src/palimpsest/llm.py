from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from ollama import Client


@dataclass()
class Completion:
    model: str
    text: str | None
    prompt_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None


@dataclass()
class ChatResponse:
    text: str | None
    tool_calls: Sequence[Any] | None


class LLM(Protocol):
    def complete(self, prompt: str) -> Completion: ...
    def chat(self, messages: list, tools: list[Callable]) -> ChatResponse: ...


class OllamaLLM:
    def __init__(self, model: str, host: str = "http://localhost:11434"):
        self._model = model
        self._client = Client(host=host)

    def complete(self, prompt: str) -> Completion:
        resp = self._client.generate(
            model=self._model, prompt=prompt, options={"temperature": 0}
        )
        return Completion(
            model=self._model,
            text=resp.response,
            prompt_tokens=resp.prompt_eval_count,
            output_tokens=resp.eval_count,
            latency_ms=resp.total_duration,
        )

    def chat(self, messages, tools) -> ChatResponse:
        response = self._client.chat(
            model=self._model,
            messages=messages,
            tools=tools,
            options={"temperature": 0},
        )
        return ChatResponse(
            text=response.message.content, tool_calls=response.message.tool_calls
        )


class AnthropicLLM:
    def __init__(self, model: str, api_key: str): ...
    def complete(self, prompt: str) -> Completion: ...
    def chat(self, messages, tools) -> ChatResponse: ...
