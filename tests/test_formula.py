import pytest

from bench29.extract.formula import STANDARD, check_equation, check_formula, equivalent, parse_math

CORRECT = [
    r"\nabla^2 f = \frac{\partial^2 f}{\partial r^2} + \frac{1}{r}\frac{\partial f}{\partial r} + \frac{1}{r^2}\frac{\partial^2 f}{\partial \theta^2}",
    r"\Delta f = \frac{1}{r}\frac{\partial}{\partial r}\left(r\frac{\partial f}{\partial r}\right) + \frac{1}{r^2}\frac{\partial^2 f}{\partial\theta^2}",
    r"\nabla^2 f = f_{rr} + \frac{1}{r} f_r + \frac{1}{r^2} f_{\theta\theta}",
    r"\nabla^2 = \frac{\partial^2}{\partial r^2} + \frac1r\frac{\partial}{\partial r} + \frac{1}{r^2}\frac{\partial^2}{\partial \theta^2}",
    r"\nabla^2 f = \partial_r^2 f + \frac{1}{r}\partial_r f + \frac{1}{r^2}\partial_\theta^2 f",
    r"\nabla^2 f = \frac{1}{r}\partial_r(r\,\partial_r f) + r^{-2}\partial_{\theta\theta} f",
    "∇²f = ∂²f/∂r² + (1/r)∂f/∂r + (1/r²)∂²f/∂θ²",
    "∇²f = f_rr + (1/r)f_r + (1/r²)f_θθ",
    r"\Delta u = \frac{\partial^{2}u}{\partial r^{2}} + \frac{1}{r}\frac{\partial u}{\partial r} + \frac{1}{r^{2}}\frac{\partial^{2}u}{\partial\theta^{2}} \qquad(r>0)",
    r"\boxed{\Delta f = \underbrace{\frac{\partial^2 f}{\partial r^2}}_{\text{前後}} + \underbrace{\frac{1}{r}\frac{\partial f}{\partial r}}_{\text{とびら}} + \underbrace{\frac{1}{r^2}\frac{\partial^2 f}{\partial\theta^2}}_{\text{左右}}}",
    r"\frac{\partial^2 f}{\partial x^2}+\frac{\partial^2 f}{\partial y^2} = \frac{\partial^2 f}{\partial r^2}+\frac{1}{r}\frac{\partial f}{\partial r}+\frac{1}{r^2}\frac{\partial^2 f}{\partial\theta^2}",
    r"\nabla^2\Phi = \frac{\partial^2 \Phi}{\partial r^2} + \frac{1}{r}\frac{\partial \Phi}{\partial r} + \frac{1}{r^2}\frac{\partial^2 \Phi}{\partial \phi^2}",
    # 途中式で三角関数が残っていても等価なら correct
    r"\nabla^2 f = (\cos^2\theta + \sin^2\theta) f_{rr} + \frac{1}{r} f_r + \frac{1}{r^2} f_{\theta\theta}",
]

INCORRECT = [
    r"\nabla^2 f = f_{rr} + \frac{1}{r} f_r + \frac{1}{r} f_{\theta\theta}",
    r"\nabla^2 f = f_{rr} + \frac{1}{r^2} f_r + \frac{1}{r^2} f_{\theta\theta}",
    r"\nabla^2 f = f_{rr} + \frac{1}{r^2} f_{\theta\theta}",
    r"\nabla^2 f = \frac{1}{r}\frac{\partial}{\partial r}\left(\frac{\partial f}{\partial r}\right) + \frac{1}{r^2} f_{\theta\theta}",
    r"\nabla^2 f = f_{rr} - \frac{1}{r} f_r + \frac{1}{r^2} f_{\theta\theta}",
]


@pytest.mark.parametrize("src", CORRECT)
def test_correct_forms(src):
    assert check_equation(src)[0] == "correct", src


@pytest.mark.parametrize("src", INCORRECT)
def test_incorrect_forms(src):
    assert check_equation(src)[0] == "incorrect", src


def test_intermediate_step_is_not_candidate():
    # f_x = ... のような連鎖律の途中式は候補にしない
    assert check_equation(r"\frac{\partial f}{\partial x} = \cos\theta f_r - \frac{\sin\theta}{r} f_\theta") is None
    assert check_equation(r"x = r\cos\theta") is None
    assert check_equation(r"\frac{u_{\theta\theta}}{r^2}=-\frac{\cos\theta}{r}") is None


def test_delta_theta_is_not_laplacian_marker():
    assert check_equation(r"d = r\Delta\theta") is None


def test_radial_identity_alone_is_not_final_formula():
    src = r"\frac{1}{r}\frac{\partial}{\partial r}\left(r\frac{\partial f}{\partial r}\right) = \frac{\partial^2 f}{\partial r^2} + \frac{1}{r}\frac{\partial f}{\partial r}"
    assert check_equation(src) is None


def test_equivalent_is_symbolic_not_textual():
    assert equivalent(parse_math(r"\frac{1}{r}\partial_r(r \partial_r f) + \frac{1}{r^2} f_{\theta\theta}"), STANDARD)


def test_check_formula_positions_and_final():
    text = (
        "ゴールはこれ:\n\n$$\\nabla^2 f = f_{rr} + \\frac1r f_r + \\frac{1}{r^2} f_{\\theta\\theta}$$\n\n"
        + "説明。" * 200
        + "\n\nまとめ:\n\n$$\\nabla^2 f = f_{rr} + \\frac1r f_r + \\frac{1}{r} f_{\\theta\\theta}$$\n"
    )
    res = check_formula(text)
    assert res.status == "incorrect"  # 最後の候補で判定
    assert res.any_incorrect
    assert res.position == "head"
    assert res.n_candidates == 2


def test_absent_and_unparseable():
    assert check_formula("ピザで考えよう。式はなし。").status == "absent"
    res = check_formula("$$\\nabla^2 f = \\mathcal{L}_{r,\\theta} f$$")
    assert res.status == "unparseable"


def test_code_formula_is_not_counted():
    text = "```python\nlap = sp.diff(f, r, 2) + sp.diff(f, r)/r + sp.diff(f, th, 2)/r**2\n```\n"
    assert check_formula(text).status == "absent"
