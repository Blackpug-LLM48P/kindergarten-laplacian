"""カテゴリ分布の基本量: 分布・エントロピー・Top-1 集中度・テンプレ一致率。"""

from __future__ import annotations

import math
from collections import Counter
from typing import Hashable, Sequence


def distribution(labels: Sequence[Hashable], support: Sequence[Hashable] | None = None) -> dict:
    """ラベル列 → 相対頻度。support を与えると 0 のカテゴリも含める。"""
    c = Counter(labels)
    n = sum(c.values())
    keys = list(support) if support is not None else sorted(c, key=str)
    if n == 0:
        return {k: 0.0 for k in keys}
    return {k: c.get(k, 0) / n for k in keys}


def entropy(labels: Sequence[Hashable], base: float = 2.0) -> float:
    """Shannon エントロピー（既定 bits）。低いほど単一アトラクタに吸われている。"""
    n = len(labels)
    if n == 0:
        return float("nan")
    h = 0.0
    for k in Counter(labels).values():
        p = k / n
        h -= p * math.log(p, base)
    return h + 0.0


def normalized_entropy(labels: Sequence[Hashable], k_support: int, base: float = 2.0) -> float:
    """H / log(K)。辞書サイズの違う版同士を比べるときの補助。"""
    if k_support <= 1:
        return float("nan")
    return entropy(labels, base) / math.log(k_support, base)


def top1(labels: Sequence[Hashable]) -> tuple[Hashable | None, float]:
    """(最頻ラベル, その比率)。「重力」の強さ。同率は文字列順で先のものを返す（決定論的）。"""
    if not labels:
        return None, float("nan")
    c = Counter(labels)
    label, k = min(c.items(), key=lambda kv: (-kv[1], str(kv[0])))
    return label, k / len(labels)


def top1_share(labels: Sequence[Hashable]) -> float:
    return top1(labels)[1]


def template_match_rate(sequences: Sequence[str]) -> float:
    """セクション系列の最頻パターンの比率。定型化の度合い。"""
    return top1_share(list(sequences))
