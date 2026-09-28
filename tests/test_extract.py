from pathlib import Path

from bench29.extract.code_audit import audit_code
from bench29.extract.features import extract_features
from bench29.extract.metaphor import load_lexicon, metaphor_features
from bench29.extract.structure import structure_features
from bench29.ingest import from_records
from bench29.schema import CodeBlock, Trial, extract_code_blocks

ROOT = Path(__file__).resolve().parents[1]


def test_metaphor_longest_match_and_order():
    f = metaphor_features("まずパンケーキを想像して。次にピザ、最後にまたピザとケーキ。")
    assert f.metaphor_primary == "pancake"  # 「ケーキ」ではない
    assert f.metaphor_categories == ["pancake", "pizza", "cake"]
    assert f.metaphor_count == 3 and f.metaphor_hits_total == 4
    assert f.metaphor_primary_group == "round_food"


def test_metaphor_english_word_boundaries():
    f = metaphor_features("Think of a pizza. Moving counterclockwise is fine; pancakes are round too.")
    assert f.metaphor_categories == ["pizza", "pancake"]  # clockwise は clock にならない


def test_metaphor_ignores_math_and_code():
    f = metaphor_features("$$\\text{pizza}$$\n```python\n# pizza\n```\n")
    assert f.metaphor_primary == "none"


def test_lexicon_loads_both_languages():
    lex = load_lexicon()
    assert lex.version.startswith("ja:") and ";en:" in lex.version


def test_structure_jargon_before_metaphor():
    s = structure_features("連鎖律を使います。\n\nピザを考えよう。", "ja", metaphor_offsets=[12])
    assert s.jargon_before_metaphor is True
    s = structure_features("ピザを考えよう。\n\n連鎖律を使います。", "ja", metaphor_offsets=[0])
    assert s.jargon_before_metaphor is False


def test_structure_sections():
    text = "# はじめに\nこんにちは\n\n## ピザで考える\nピザの切れ目。\n\n## 導出\n$$f_{rr}+\\frac1r f_r$$\n\n## まとめ\nおしまい"
    s = structure_features(text, "ja", metaphor_offsets=[text.index("ピザの")])
    assert s.section_tags == ["intro", "metaphor", "derivation", "summary"]
    assert s.n_headings == 4 and s.n_math_blocks == 1


SYMBOLIC_DERIVATION = """
import sympy as sp
r, th = sp.symbols('r theta', positive=True)
x, y = sp.symbols('x y')
f = sp.Function('f')
F = f(r*sp.cos(th), r*sp.sin(th))
lap = sp.diff(F, r, 2) + sp.diff(F, r)/r + sp.diff(F, th, 2)/r**2
print(sp.simplify(lap))
"""

SYMBOLIC_CHECK = """
import sympy as sp
x, y, r, th = sp.symbols('x y r theta')
g = x**3 - x*y**2
cart = sp.diff(g, x, 2) + sp.diff(g, y, 2)
p = g.subs({x: r*sp.cos(th), y: r*sp.sin(th)})
polar = sp.diff(p, r, 2) + sp.diff(p, r)/r + sp.diff(p, th, 2)/r**2
print(sp.simplify(polar - cart.subs({x: r*sp.cos(th), y: r*sp.sin(th)})))
"""

CIRCULAR = """
import sympy as sp
r, th = sp.symbols('r theta', positive=True)
f = r**2 * sp.cos(2*th)
lap = sp.diff(f, r, 2) + sp.diff(f, r)/r + sp.diff(f, th, 2)/r**2
expected = sp.diff(f, r, 2) + sp.diff(f, r)/r + sp.diff(f, th, 2)/r**2
assert sp.simplify(lap - expected) == 0
"""

PLOT_ONLY = """
import numpy as np
import matplotlib.pyplot as plt
r = np.linspace(0.1, 5, 100)
plt.plot(r, np.sin(r)/r)
plt.show()
"""


def _audit(code):
    return audit_code([CodeBlock("python", code)])


def test_verification_types():
    assert _audit(SYMBOLIC_DERIVATION).verification_type == "symbolic_derivation"
    a = _audit(SYMBOLIC_CHECK)
    assert a.verification_type == "symbolic_check" and not a.circular_verification_candidate
    c = _audit(CIRCULAR)
    assert c.has_polar_formula_literal and c.circular_verification_candidate
    p = _audit(PLOT_ONLY)
    assert p.verification_type == "none" and p.uses_plot
    assert audit_code([]).code_present is False


def test_numeric_check_math_py():
    code = (ROOT / "records/2026-09-28-astra-ultra/verification/check_math.py").read_text(encoding="utf-8")
    a = _audit(code)
    assert a.verification_type == "numeric"
    assert a.has_cartesian_reference and not a.circular_verification_candidate


def test_code_blocks_skip_math_fences():
    blocks = extract_code_blocks("```math\nx\n```\n```python\nprint(1)\n```\n")
    assert [b.language for b in blocks] == ["python"]


def test_records_end_to_end():
    trials = from_records(ROOT / "records")
    assert {t.model for t in trials} == {"gpt-astra-max", "fugu", "gpt-astra-ultra"}
    rows = {t.model: extract_features(t) for t in trials}
    # 3 件とも最終式は正しい（fugu の評価記録「完成式は正しい」、astra-ultra の訂正記録と一致すること）
    for model, row in rows.items():
        assert row["formula_status"] == "correct", model
    assert rows["fugu"]["formula_position"] == "head"  # 冒頭でゴールを提示している
    assert rows["fugu"]["metaphor_primary"] == "neighbors"
    assert rows["gpt-astra-max"]["metaphor_primary_group"] == "round_food"


def test_trial_validation():
    import pytest

    with pytest.raises(ValueError):
        Trial("t", "m", "", "api", "ja", "x")
    with pytest.raises(ValueError):
        Trial("t", "m", "v1", "web", "ja", "x")
