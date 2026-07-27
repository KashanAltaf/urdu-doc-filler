"""Lightweight RAG retrieve using Gemini free embeddings + cosine similarity."""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np


@dataclass
class RagIndex:
    chunks: list[str]
    embeddings: np.ndarray  # shape (n, d)


def _client():
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY سیٹ نہیں ہے۔ Google AI Studio سے مفت کلید لیں: https://aistudio.google.com/apikey"
        )
    return genai.Client(api_key=api_key)


def embed_texts(
    texts: list[str],
    *,
    model: str | None = None,
) -> np.ndarray:
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    # text-embedding-004 was shut down; use current Gemini embedding model
    model = model or os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-2")
    client = _client()
    vectors: list[list[float]] = []

    def _values_from_response(result) -> list[list[float]]:
        out: list[list[float]] = []
        embs = getattr(result, "embeddings", None)
        if embs:
            for e in embs:
                values = getattr(e, "values", None)
                out.append(list(values if values is not None else e))
            return out
        emb = getattr(result, "embedding", None)
        if emb is not None:
            values = getattr(emb, "values", None)
            return [list(values if values is not None else emb)]
        raise RuntimeError("Embedding جواب درست نہیں۔")

    def _embed_once(contents):
        try:
            return client.models.embed_content(model=model, contents=contents)
        except Exception as first:
            fallback = (
                "gemini-embedding-001"
                if model != "gemini-embedding-001"
                else "gemini-embedding-2"
            )
            if fallback == model:
                raise first
            try:
                return client.models.embed_content(model=fallback, contents=contents)
            except Exception:
                raise first

    # Prefer small batches; fall back to one-by-one if batch shape differs
    batch_size = 8
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        try:
            result = _embed_once(batch)
            got = _values_from_response(result)
            if len(got) != len(batch):
                raise RuntimeError("batch size mismatch")
            vectors.extend(got)
        except Exception:
            for item in batch:
                result = _embed_once(item)
                vectors.extend(_values_from_response(result))

    arr = np.array(vectors, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


def build_index(chunks: list[str]) -> RagIndex:
    if not chunks:
        raise ValueError("کتاب سے کوئی متن نہیں ملا۔")
    embs = embed_texts(chunks)
    return RagIndex(chunks=chunks, embeddings=embs)


def retrieve(index: RagIndex, query: str, top_k: int = 6) -> list[str]:
    if not query.strip():
        return index.chunks[:top_k]
    q = embed_texts([query])[0]
    scores = index.embeddings @ q
    k = min(top_k, len(index.chunks))
    idxs = np.argsort(-scores)[:k]
    return [index.chunks[int(i)] for i in idxs]
