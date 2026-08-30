from dataclasses import dataclass
from typing import Protocol

from ollama import Client


@dataclass()
class Completion:
    model: str
    text: str | None
    prompt_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None


class LLM(Protocol):
    def complete(self, prompt: str) -> Completion: ...


class OllamaLLM:
    def __init__(self, model: str, host: str = "http://localhost:11434"):
        self._model = model
        self._client = Client(host=host)

    def complete(self, prompt: str) -> Completion:
        resp = self._client.generate(model=self._model, prompt=prompt)
        return Completion(
            model=self._model,
            text=resp.response,
            prompt_tokens=resp.prompt_eval_count,
            output_tokens=resp.eval_count,
            latency_ms=resp.total_duration,
        )


class AnthropicLLM:
    def __init__(self, model: str, api_key: str): ...
    def complete(self, prompt: str) -> Completion: ...
