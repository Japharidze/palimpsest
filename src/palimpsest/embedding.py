from collections.abc import Sequence
from typing import Protocol

from ollama import Client

from palimpsest.config import settings


class Embedder(Protocol):
    def embed(self, text: str) -> Sequence[float]: ...
    def embed_batch(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


class OllamaEmbedder:
    def __init__(self, model: str, host: str = "http://localhost:11434"):
        self._model = model
        self._client = Client(host=host)

    def embed(self, text: str) -> Sequence[float]:
        resp = self._client.embed(model=self._model, input=text)
        return resp.embeddings[0]

    def embed_batch(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        resp = self._client.embed(model=self._model, input=list(texts))
        return resp.embeddings


class OpenAIEmbedder:
    def __init__(self, model: str, api_key: str):
        from openai import OpenAI

        self._model = model
        self._client = OpenAI(api_key=api_key)

    def embed_batch(self, texts):
        r = self._client.embeddings.create(
            model=self._model, input=list(texts), dimensions=768
        )
        return [d.embedding for d in r.data]

    def embed(self, text):
        return self.embed_batch([text])[0]


def build_embedder() -> Embedder:
    provider = settings.embedding_provider

    if provider == "ollama":
        return OllamaEmbedder(settings.embedding_model)

    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set")
        return OpenAIEmbedder(settings.embedding_model, settings.openai_api_key)

    raise ValueError(f"unknown embedding provider {provider!r}")
