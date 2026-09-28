"""意味的多様性: 応答埋め込みのペアワイズ cos 類似度の平均。高い = モード崩壊。

埋め込みは差し替え可能な部品。結果には必ず embedder 名を記録し、
比較は同一 embedder 内でのみ行う（profiles.json の embedder フィールドで照合）。

既定の HashingNgramEmbedder は外部モデル不要・完全決定論の文字 n-gram 埋め込み。
「表層の似通い」しか測らないので、本番の意味的多様性には別の埋め込みを選ぶこと
（未決事項: 埋め込みモデルの選定）。
"""

from __future__ import annotations

import math
import zlib
from collections import Counter
from typing import Protocol, Sequence

import numpy as np

from .bootstrap import DEFAULT_B, DEFAULT_SEED, Estimate, _ci


class Embedder(Protocol):
    name: str

    def embed(self, texts: Sequence[str]) -> np.ndarray: ...


class HashingNgramEmbedder:
    def __init__(self, n: int = 3, dim: int = 1 << 14):
        self.n = n
        self.dim = dim
        self.name = f"hashing-char{n}gram-d{dim}"

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float64)
        for i, t in enumerate(texts):
            t = " ".join(t.split())
            grams = Counter(t[j : j + self.n] for j in range(max(len(t) - self.n + 1, 0)))
            for g, c in grams.items():
                out[i, zlib.crc32(g.encode("utf-8")) % self.dim] += 1.0 + math.log(c)
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return out / norms


class SentenceTransformerEmbedder:
    """sentence-transformers が入っていれば使える差し替え例。モデル名は結果に記録される。"""

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # 任意依存

        self._m = SentenceTransformer(model_name)
        self.name = f"st:{model_name}"

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        return np.asarray(self._m.encode(list(texts), normalize_embeddings=True), dtype=np.float64)


def similarity_matrix(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    v = vectors / norms
    return v @ v.T


def mean_pairwise_similarity(sim: np.ndarray, idx: np.ndarray | None = None) -> float:
    """idx で選んだ標本間の平均類似度。同一元応答どうしのペア（ブートストラップの重複）は除く。"""
    if idx is None:
        idx = np.arange(sim.shape[0])
    if len(idx) < 2:
        return float("nan")
    sub = sim[np.ix_(idx, idx)]
    mask = idx[:, None] != idx[None, :]
    return float(sub[mask].mean()) if mask.any() else float("nan")


def diversity(texts: Sequence[str], embedder: Embedder | None = None, b: int = DEFAULT_B,
              seed: int = DEFAULT_SEED) -> tuple[Estimate, str]:
    embedder = embedder or HashingNgramEmbedder()
    n = len(texts)
    if n < 2:
        return Estimate(float("nan"), float("nan"), float("nan"), n), embedder.name
    sim = similarity_matrix(embedder.embed(texts))
    value = mean_pairwise_similarity(sim)
    rng = np.random.default_rng(seed)
    samples = np.array([mean_pairwise_similarity(sim, rng.integers(0, n, size=n)) for _ in range(b)])
    lo, hi = _ci(samples, 0.05)
    return Estimate(value, lo, hi, n), embedder.name
