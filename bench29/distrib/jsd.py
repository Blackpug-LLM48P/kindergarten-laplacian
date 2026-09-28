"""Jensen–Shannon ダイバージェンス（base 2、値域 [0, 1]）。

モデル間: 比喩分布・構造系列分布の距離（性格差）。
バージョン間: 同一モデルの世代間ドリフト（時系列で残る最重要シグナル）。
"""

from __future__ import annotations

import math
from typing import Hashable, Sequence

from .entropy import distribution


def jsd_from_dists(p: dict, q: dict) -> float:
    keys = set(p) | set(q)
    m = {k: 0.5 * (p.get(k, 0.0) + q.get(k, 0.0)) for k in keys}

    def kl(a: dict) -> float:
        return sum(a[k] * math.log2(a[k] / m[k]) for k in a if a[k] > 0)

    return max(0.0, 0.5 * kl(p) + 0.5 * kl(q))


def jsd(labels_a: Sequence[Hashable], labels_b: Sequence[Hashable]) -> float:
    if not labels_a or not labels_b:
        return float("nan")
    support = sorted(set(labels_a) | set(labels_b), key=str)
    return jsd_from_dists(distribution(labels_a, support), distribution(labels_b, support))
