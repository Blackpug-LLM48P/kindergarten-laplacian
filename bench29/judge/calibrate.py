"""judge ドリフト対策: 人手ラベル付きアンカーセットで Cohen's κ を測る。

anchors/*.jsonl の 1 行:
  {"trial": {...Trial...}, "labels": {"<labeler_id>": {"stretch_level": 2, "drift": false, ...}}}

- ラベラーが複数なら、軸ごとに多数決（同数は「人手不一致」として κ 計算から除外）で参照ラベルを作り、
  ラベラー間 κ も併記する（未決事項: 単独か複数か。どちらでも動く）。
- judge 更新時・定期的に再採点し、全軸の κ が閾値以上なら採用。1 軸でも下回れば不採用。
"""

from __future__ import annotations

import datetime as _dt
import json
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any, Hashable, Sequence

from ..schema import Trial
from .run_judge import BINARY_AXES, JudgeClient, judge_trial, rubric_version

DEFAULT_THRESHOLD = 0.6  # 暫定。閾値の最終値は黒パグ判断
AXES = ("stretch_level",) + BINARY_AXES


def cohen_kappa(a: Sequence[Hashable], b: Sequence[Hashable], weights: str | None = None) -> float:
    """Cohen's κ。weights="quadratic" で順序尺度（stretch_level）用の重み付き κ。"""
    if len(a) != len(b):
        raise ValueError("length mismatch")
    n = len(a)
    if n == 0:
        return float("nan")
    cats = sorted(set(a) | set(b), key=lambda x: (str(type(x)), x))
    k = len(cats)
    if k == 1:
        return 1.0  # 両者が全件同じ単一カテゴリ: 一致しているが κ は定義上不定。1.0 として扱い、件数で注記する
    idx = {c: i for i, c in enumerate(cats)}
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[idx[x]][idx[y]] += 1
    ra = [sum(row) for row in obs]
    cb = [sum(obs[i][j] for i in range(k)) for j in range(k)]

    def w(i: int, j: int) -> float:
        if weights == "quadratic":
            return ((i - j) / (k - 1)) ** 2
        return 0.0 if i == j else 1.0

    po = sum(w(i, j) * obs[i][j] for i in range(k) for j in range(k)) / n
    pe = sum(w(i, j) * ra[i] * cb[j] for i in range(k) for j in range(k)) / (n * n)
    if pe == 0:
        return 1.0 if po == 0 else float("nan")
    return 1.0 - po / pe


def load_anchors(path: str | Path) -> list[dict[str, Any]]:
    files = sorted(Path(path).glob("*.jsonl")) if Path(path).is_dir() else [Path(path)]
    out = []
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                d["trial"] = Trial.from_dict(d["trial"])
                out.append(d)
    return out


def reference_label(labels: dict[str, dict], axis: str) -> Any:
    votes = Counter(v[axis] for v in labels.values() if axis in v)
    if not votes:
        return None
    (top, c), *rest = votes.most_common()
    if rest and rest[0][1] == c:
        return None
    return top


def inter_labeler_kappa(anchors: list[dict], axis: str) -> dict[str, float]:
    labelers = sorted({lab for a in anchors for lab in a["labels"]})
    out = {}
    for x, y in combinations(labelers, 2):
        pairs = [(a["labels"][x][axis], a["labels"][y][axis]) for a in anchors
                 if axis in a["labels"].get(x, {}) and axis in a["labels"].get(y, {})]
        if pairs:
            out[f"{x}~{y}"] = cohen_kappa(*zip(*pairs), weights="quadratic" if axis == "stretch_level" else None)
    return out


def calibrate(anchors: list[dict], client: JudgeClient, threshold: float = DEFAULT_THRESHOLD,
              l1_by_id: dict[str, dict] | None = None) -> dict[str, Any]:
    judged = {a["trial"].trial_id: judge_trial(a["trial"], client, (l1_by_id or {}).get(a["trial"].trial_id))
              for a in anchors}
    return score(anchors, judged, threshold, client.model,
                 next(iter(judged.values()))["judge_version"] if judged else None)


def score(anchors: list[dict], judged: dict[str, dict], threshold: float = DEFAULT_THRESHOLD,
          judge_model: str | None = None, judge_version: str | None = None) -> dict[str, Any]:
    per_axis = {}
    for axis in AXES:
        ref, got = [], []
        for a in anchors:
            r = reference_label(a["labels"], axis)
            j = judged.get(a["trial"].trial_id, {}).get(axis)
            if r is None or j is None:
                continue
            ref.append(r)
            got.append(j)
        kappa = cohen_kappa(ref, got, weights="quadratic" if axis == "stretch_level" else None)
        per_axis[axis] = {
            "kappa": None if kappa != kappa else round(kappa, 4),
            "n": len(ref),
            "agreement": round(sum(x == y for x, y in zip(ref, got)) / len(ref), 4) if ref else None,
            "inter_labeler_kappa": {k: round(v, 4) for k, v in inter_labeler_kappa(anchors, axis).items()},
        }
    kappas = [v["kappa"] for v in per_axis.values() if v["kappa"] is not None]
    accepted = bool(kappas) and min(kappas) >= threshold
    return {
        "calibrated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "judge_model": judge_model,
        "judge_version": judge_version,
        "rubric_version": rubric_version(),
        "n_anchors": len(anchors),
        "threshold": threshold,
        "accepted": accepted,
        "decision": "adopt" if accepted else "reject judge update, or re-judge all trials",
        "axes": per_axis,
    }
