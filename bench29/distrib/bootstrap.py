"""パーセンタイル・ブートストラップ 95% CI。全 Layer 2 指標に付ける。

乱数シードは固定（再実行で同じ CI）。2 群統計量（JSD など）は両群を独立に再標本化する。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

DEFAULT_B = 2000
DEFAULT_SEED = 29


@dataclass
class Estimate:
    value: float
    lo: float
    hi: float
    n: int

    def to_dict(self) -> dict:
        return {"value": _r(self.value), "ci95": [_r(self.lo), _r(self.hi)], "n": self.n}


def _r(x: float) -> float | None:
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 6)


def _ci(samples: np.ndarray, alpha: float) -> tuple[float, float]:
    samples = samples[~np.isnan(samples)]
    if samples.size == 0:
        return float("nan"), float("nan")
    return float(np.quantile(samples, alpha / 2)), float(np.quantile(samples, 1 - alpha / 2))


def bootstrap(data: Sequence, stat: Callable[[list], float], b: int = DEFAULT_B, alpha: float = 0.05,
              seed: int = DEFAULT_SEED) -> Estimate:
    data = list(data)
    n = len(data)
    if n == 0:
        return Estimate(float("nan"), float("nan"), float("nan"), 0)
    value = stat(data)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(b, n))
    samples = np.array([stat([data[i] for i in row]) for row in idx], dtype=float)
    lo, hi = _ci(samples, alpha)
    return Estimate(value, lo, hi, n)


def bootstrap2(a: Sequence, b_: Sequence, stat: Callable[[list, list], float], b: int = DEFAULT_B,
               alpha: float = 0.05, seed: int = DEFAULT_SEED) -> Estimate:
    a, b_ = list(a), list(b_)
    if not a or not b_:
        return Estimate(float("nan"), float("nan"), float("nan"), min(len(a), len(b_)))
    value = stat(a, b_)
    rng = np.random.default_rng(seed)
    ia = rng.integers(0, len(a), size=(b, len(a)))
    ib = rng.integers(0, len(b_), size=(b, len(b_)))
    samples = np.array([stat([a[i] for i in ra], [b_[j] for j in rb]) for ra, rb in zip(ia, ib)], dtype=float)
    lo, hi = _ci(samples, alpha)
    return Estimate(value, lo, hi, min(len(a), len(b_)))
