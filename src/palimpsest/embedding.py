from collections.abc import Sequence
from typing import Protocol

from ollama import Client


class Embedder(Protocol):
    def embed(self, text: str) -> Sequence[float]: ...

class OllamaEmbedder:
    def __init__(self, model: str = "nomic-embed-text", host: str = "http://localhost:11434"):
        self._model = model
        self._client = Client(host=host)

    def embed(self, text: str) -> Sequence[float]:
        resp = self._client.embed(model=self._model, input=text)
        return resp.embeddings[0]

    def embed_batch(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        resp = self._client.embed(model=self._model, input=texts)
        return resp.embeddings

