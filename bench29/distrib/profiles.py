"""features（trial 単位）→ profiles（セル単位の Layer 2 指標 + ブートストラップ 95% CI）。

総合点には集約しない。出力はセルごとの「指紋ベクトル」と、セル間の JSD。
"""

from __future__ import annotations

import datetime as _dt
import json
from itertools import combinations
from typing import Any, Sequence

import numpy as np

from .. import FEATURE_VERSION
from .bootstrap import DEFAULT_B, DEFAULT_SEED, Estimate, _ci
from .diversity import Embedder, HashingNgramEmbedder, diversity

DEFAULT_CELL_KEYS = ("model", "model_version", "lang", "surface")
MIN_N = 100

CATEGORICAL = {
    "metaphor": "metaphor_primary",
    "metaphor_group": "metaphor_primary_group",
    "structure": "section_sequence",
    "verification_type": "verification_type",
    "formula_status": "formula_status",
    "formula_position": "formula_position",
}
RATES = {
    "formula_correct": ("formula_status", "correct"),
    "code_present": ("code_present", True),
    "uses_sympy": ("uses_sympy", True),
    "circular_verification_candidate": ("circular_verification_candidate", True),
    "jargon_before_metaphor": ("jargon_before_metaphor", True),
    "no_metaphor": ("metaphor_primary", "none"),
}
MEANS = ("n_chars", "n_headings", "n_steps", "n_math_blocks", "metaphor_count", "avg_sentence_len", "symbol_density")


# ---------------------------------------------------------------- ベクトル化したカテゴリ統計

class _Counts:
    """ラベル列を one-hot にしておき、ブートストラップの再標本化をまとめて行う。"""

    def __init__(self, labels: Sequence, support: Sequence | None = None, b: int = DEFAULT_B,
                 seed: int = DEFAULT_SEED):
        self.labels = [_key(x) for x in labels]
        self.support = list(support) if support is not None else sorted(set(self.labels), key=str)
        pos = {k: i for i, k in enumerate(self.support)}
        n, k = len(self.labels), len(self.support)
        self.n = n
        codes = np.array([pos[lab] for lab in self.labels], dtype=np.int64)
        self.obs = np.bincount(codes, minlength=k).astype(float)
        if n:
            rng = np.random.default_rng(seed)
            flat = codes[rng.integers(0, n, size=(b, n))] + (np.arange(b) * k)[:, None]
            self.boot = np.bincount(flat.ravel(), minlength=b * k).reshape(b, k).astype(float)
        else:
            self.boot = np.zeros((0, k))

    def proportions(self) -> dict:
        out = {}
        for j, lab in enumerate(self.support):
            lo, hi = _ci(self.boot[:, j] / self.n, 0.05)
            out[str(lab)] = Estimate(self.obs[j] / self.n, lo, hi, self.n).to_dict()
        return out

    def entropy(self) -> Estimate:
        return Estimate(_H(self.obs), *_ci(_H(self.boot), 0.05), self.n)

    def top1(self) -> dict:
        j = int(np.argmax(self.obs))
        share = self.boot.max(axis=1) / self.n
        est = Estimate(self.obs[j] / self.n, *_ci(share, 0.05), self.n).to_dict()
        est["label"] = str(self.support[j])
        return est


def _key(x: Any) -> Any:
    return "null" if x is None or (isinstance(x, float) and np.isnan(x)) else x


def _H(counts: np.ndarray) -> np.ndarray | float:
    c = np.atleast_2d(counts).astype(float)
    tot = c.sum(axis=1, keepdims=True)
    p = np.divide(c, tot, out=np.zeros_like(c), where=tot > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        h = -np.nansum(np.where(p > 0, p * np.log2(p), 0.0), axis=1)
    return float(h[0]) if np.ndim(counts) == 1 else h


def _jsd_counts(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = np.atleast_2d(a).astype(float)
    b = np.atleast_2d(b).astype(float)
    p = a / a.sum(axis=1, keepdims=True)
    q = b / b.sum(axis=1, keepdims=True)
    m = 0.5 * (p + q)
    with np.errstate(divide="ignore", invalid="ignore"):
        kl = lambda x: np.nansum(np.where(x > 0, x * np.log2(x / m), 0.0), axis=1)
        return np.clip(0.5 * kl(p) + 0.5 * kl(q), 0.0, 1.0)


def boot_mean(values: Sequence[float], b: int = DEFAULT_B, seed: int = DEFAULT_SEED) -> Estimate:
    v = np.asarray(values, dtype=float)
    if v.size == 0:
        return Estimate(float("nan"), float("nan"), float("nan"), 0)
    rng = np.random.default_rng(seed)
    lo, hi = _ci(v[rng.integers(0, v.size, size=(b, v.size))].mean(axis=1), 0.05)
    return Estimate(float(v.mean()), lo, hi, int(v.size))


def jsd_estimate(labels_a: Sequence, labels_b: Sequence, b: int = DEFAULT_B, seed: int = DEFAULT_SEED) -> Estimate:
    if not labels_a or not labels_b:
        return Estimate(float("nan"), float("nan"), float("nan"), 0)
    support = sorted({_key(x) for x in labels_a} | {_key(x) for x in labels_b}, key=str)
    ca = _Counts(labels_a, support, b, seed)
    cb = _Counts(labels_b, support, b, seed + 1)
    value = float(_jsd_counts(ca.obs, cb.obs)[0])
    lo, hi = _ci(_jsd_counts(ca.boot, cb.boot), 0.05)
    return Estimate(value, lo, hi, min(ca.n, cb.n))


# ---------------------------------------------------------------- セル集計

def _cells(rows: list[dict], keys: Sequence[str]) -> dict[tuple, list[dict]]:
    out: dict[tuple, list[dict]] = {}
    for r in rows:
        out.setdefault(tuple(r[k] for k in keys), []).append(r)
    return dict(sorted(out.items(), key=lambda kv: tuple(str(x) for x in kv[0])))


def cell_metrics(rows: list[dict], texts: list[str] | None, embedder: Embedder, b: int, seed: int) -> dict:
    m: dict[str, Any] = {}
    for name, col in CATEGORICAL.items():
        c = _Counts([r.get(col) for r in rows], b=b, seed=seed)
        m[f"{name}_distribution"] = c.proportions()
        if name in ("metaphor", "metaphor_group"):
            m[f"{name}_entropy"] = c.entropy().to_dict()
            m[f"{name}_top1"] = c.top1()
        if name == "structure":
            m["structure_template_match_rate"] = c.top1()
            m["structure_entropy"] = c.entropy().to_dict()
    for name, (col, val) in RATES.items():
        vals = [float(r.get(col) == val) for r in rows if _key(r.get(col)) != "null"]
        m[f"rate_{name}"] = boot_mean(vals, b, seed).to_dict()
    for col in MEANS:
        vals = [float(r[col]) for r in rows if _key(r.get(col)) != "null"]
        m[f"mean_{col}"] = boot_mean(vals, b, seed).to_dict()
    if texts is not None:
        est, _ = diversity(texts, embedder, b=b, seed=seed)
        m["semantic_similarity"] = est.to_dict()
    return m


def _relation(a: dict, b: dict) -> str | None:
    same = {k: a.get(k) == b.get(k) for k in DEFAULT_CELL_KEYS if k in a}
    diff = [k for k, s in same.items() if not s]
    if diff == ["model_version"]:
        return "version"
    if "model" in diff and all(same.get(k, True) for k in ("lang", "surface")):
        return "model"
    if diff == ["lang"]:
        return "lang"
    if diff == ["surface"]:
        return "surface"
    return None


def build_profiles(rows: list[dict], texts: dict[str, str] | None = None,
                   cell_keys: Sequence[str] = DEFAULT_CELL_KEYS, embedder: Embedder | None = None,
                   b: int = DEFAULT_B, seed: int = DEFAULT_SEED, min_n: int = MIN_N) -> dict:
    """rows: extract_features の出力。texts: trial_id → response_text（多様性に使用、省略可）。"""
    embedder = embedder or HashingNgramEmbedder()
    cells = _cells(rows, cell_keys)
    out_cells = []
    for key, rs in cells.items():
        cell = dict(zip(cell_keys, key))
        t = [texts[r["trial_id"]] for r in rs] if texts is not None else None
        out_cells.append({
            "cell": cell,
            "n": len(rs),
            "underpowered": len(rs) < min_n,
            "metrics": cell_metrics(rs, t, embedder, b, seed),
        })

    comparisons = []
    for (ka, ra), (kb, rb) in combinations(cells.items(), 2):
        ca, cb = dict(zip(cell_keys, ka)), dict(zip(cell_keys, kb))
        rel = _relation(ca, cb)
        if rel is None:
            continue
        comparisons.append({
            "relation": rel,
            "a": ca,
            "b": cb,
            "jsd": {name: jsd_estimate([r.get(col) for r in ra], [r.get(col) for r in rb], b, seed).to_dict()
                    for name, col in CATEGORICAL.items()},
        })

    lex_versions = sorted({r.get("lexicon_version") for r in rows if r.get("lexicon_version")})
    return {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "feature_version": FEATURE_VERSION,
        "lexicon_version": lex_versions,
        "embedder": embedder.name if texts is not None else None,
        "bootstrap": {"B": b, "seed": seed, "ci": 0.95, "method": "percentile"},
        "cell_keys": list(cell_keys),
        "min_n_recommended": min_n,
        "cells": out_cells,
        "comparisons": comparisons,
    }


def dump_profiles(profiles: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(profiles, fh, ensure_ascii=False, indent=2, default=str)
