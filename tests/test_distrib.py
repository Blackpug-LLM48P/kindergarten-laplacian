import math
import random

import pytest

from bench29.distrib.bootstrap import bootstrap
from bench29.distrib.diversity import HashingNgramEmbedder, diversity
from bench29.distrib.entropy import entropy, template_match_rate, top1
from bench29.distrib.jsd import jsd
from bench29.distrib.profiles import build_profiles, jsd_estimate
from bench29.judge.calibrate import cohen_kappa
from bench29.report import drift_report, profile_card


def test_entropy_and_top1():
    assert entropy(["a"] * 10) == 0
    assert math.isclose(entropy(["a", "b"] * 5), 1.0)
    assert top1(["pizza"] * 9 + ["cake"]) == ("pizza", 0.9)
    assert template_match_rate(["a>b", "a>b", "c"]) == pytest.approx(2 / 3)


def test_jsd_bounds():
    assert jsd(["a"] * 5, ["a"] * 5) == 0
    assert math.isclose(jsd(["a"] * 5, ["b"] * 5), 1.0)
    assert 0 < jsd(["a", "b"], ["a", "a", "b"]) < 1


def test_jsd_estimate_ci_contains_value():
    rng = random.Random(0)
    a = [rng.choice("ab") for _ in range(100)]
    b = [rng.choice("abc") for _ in range(100)]
    est = jsd_estimate(a, b, b=300)
    assert est.lo <= est.value <= est.hi


def test_bootstrap_deterministic():
    data = list(range(50))
    e1 = bootstrap(data, lambda xs: sum(xs) / len(xs), b=200)
    e2 = bootstrap(data, lambda xs: sum(xs) / len(xs), b=200)
    assert (e1.lo, e1.hi) == (e2.lo, e2.hi) and e1.lo < 24.5 < e1.hi


def test_diversity_detects_mode_collapse():
    same, _ = diversity(["ピザを切ると外側が広い"] * 10, HashingNgramEmbedder(), b=50)
    varied, name = diversity(["ピザ", "トランポリンが伸びる", "年輪を数える", "running track lanes"], b=50)
    assert same.value > 0.99 and varied.value < 0.3
    assert name.startswith("hashing-char3gram")


def test_kappa():
    assert cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1.0
    assert cohen_kappa([1, 0, 1, 0], [0, 1, 0, 1]) == -1.0
    assert cohen_kappa([0, 1, 2, 3], [0, 1, 2, 3], weights="quadratic") == 1.0


def _rows(model, version, n, pizza_share, seed):
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        m = "pizza" if rng.random() < pizza_share else rng.choice(["cake", "ripple", "none"])
        rows.append({
            "trial_id": f"{model}-{version}-{i}", "model": model, "model_version": version, "lang": "ja",
            "surface": "chat", "metaphor_primary": m, "metaphor_primary_group": "round_food",
            "section_sequence": rng.choice(["intro>metaphor>derivation>summary", "intro>derivation>code"]),
            "verification_type": rng.choice(["none", "numeric"]), "formula_status": "correct",
            "formula_position": "tail", "code_present": True, "uses_sympy": False,
            "circular_verification_candidate": False, "jargon_before_metaphor": False,
            "n_chars": 1000, "n_headings": 3, "n_steps": 2, "n_math_blocks": 2, "metaphor_count": 1,
            "avg_sentence_len": 20.0, "symbol_density": 0.1, "lexicon_version": "ja:x;en:y",
        })
    return rows


def test_profiles_reproduce_attractor_and_drift(tmp_path):
    # 「ピザ 90%」型のアトラクタを合成データで再現できるか
    rows = _rows("grok", "v1", 120, 0.9, 1) + _rows("grok", "v2", 120, 0.3, 2) + _rows("other", "v1", 40, 0.2, 3)
    texts = {r["trial_id"]: f"{r['metaphor_primary']} の説明 {i}" for i, r in enumerate(rows)}
    prof = build_profiles(rows, texts, b=200)
    cells = {(c["cell"]["model"], c["cell"]["model_version"]): c for c in prof["cells"]}
    top = cells[("grok", "v1")]["metrics"]["metaphor_top1"]
    assert top["label"] == "pizza" and 0.8 < top["value"] < 0.97
    assert cells[("other", "v1")]["underpowered"] and not cells[("grok", "v1")]["underpowered"]
    version = [c for c in prof["comparisons"] if c["relation"] == "version"]
    assert len(version) == 1 and version[0]["jsd"]["metaphor"]["ci95"][0] > 0.05
    assert {c["relation"] for c in prof["comparisons"]} == {"version", "model"}

    html = profile_card.render(prof)
    assert "grok / v1 / ja / chat" in html and "<svg" in html
    md = drift_report.render(prof)
    assert "`v1` → `v2`" in md
