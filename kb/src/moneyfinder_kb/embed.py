"""Text embeddings via Amazon Bedrock (Titan Text Embeddings V2). Disabled when EMBED_MODEL is unset."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Protocol

from .config import Settings

SCHEMA_DIM = 1024  # must match DIMENSION on chunk_vec in schema.surql


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class BedrockTitan:
    def __init__(self, model_id: str, region: str, dim: int, workers: int = 8):
        import boto3

        self.model_id = model_id
        self.dim = dim
        self.workers = workers
        self._client = boto3.client("bedrock-runtime", region_name=region)

    def _one(self, text: str) -> list[float]:
        body = json.dumps({"inputText": text, "dimensions": self.dim, "normalize": True})
        resp = self._client.invoke_model(
            modelId=self.model_id, body=body, contentType="application/json", accept="application/json"
        )
        return json.loads(resp["body"].read())["embedding"]

    def embed(self, texts: list[str]) -> list[list[float]]:
        # Titan V2 takes one input per call; run calls in parallel.
        with ThreadPoolExecutor(self.workers) as pool:
            return list(pool.map(self._one, texts))


def make_embedder(settings: Settings) -> Embedder | None:
    if not settings.embed_model:
        return None
    if settings.embed_dim != SCHEMA_DIM:
        raise ValueError(
            f"EMBED_DIM={settings.embed_dim} but the chunk_vec index is {SCHEMA_DIM}-d; change both together"
        )
    return BedrockTitan(settings.embed_model, settings.aws_region, settings.embed_dim)
