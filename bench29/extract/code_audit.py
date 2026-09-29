"""Python 使用の監査: 何を検証したか（verification_type）と循環検証の候補。

verification_type（主タイプ。複数該当時はこの優先順）:
  symbolic_derivation  汎用関数 f(x, y) と x=r cosθ, y=r sinθ から連鎖律で極座標形を導く
  symbolic_check       具体的な関数で、極座標公式と直交座標のラプラシアンを SymPy で突き合わせる
  numeric              格子上・有限差分・数値評価での比較
  none                 コードなし、または検証に当たる処理なし（描画だけ等）

circular_verification_candidate:
  目標の極座標公式がコード中に書かれているのに、独立した参照（直交座標での計算）がないもの。
  「公式をそれ自身と比べているだけ」の疑い。最終判定は Layer 3 の judge が行う。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..schema import CodeBlock

PY_LANGS = {"python", "py", "python3", "ipython", "sympy", ""}

_SYMPY = re.compile(r"\bimport\s+sympy\b|\bfrom\s+sympy\b|\bsympy\.|\bsp\.(diff|symbols|Function|simplify)")
_NUMPY = re.compile(r"\bimport\s+numpy\b|\bfrom\s+numpy\b|\bnp\.")
_PLOT = re.compile(r"matplotlib|plt\.|plotly|\.plot\(|imshow|contour")

_GENERIC_FUNC = re.compile(r"Function\(\s*['\"]\w+['\"]\s*\)")
_POLAR_TRANSFORM = re.compile(r"r\s*\*\s*(?:sp\.|sympy\.|np\.|math\.)?cos\s*\(\s*(?:theta|th|t|phi|θ)", re.I)
_DIFF_WRT = lambda var: re.compile(rf"diff\([^()]*(?:\([^()]*\)[^()]*)*,\s*{var}\b|Derivative\([^)]*,\s*{var}\b|\.diff\(\s*{var}\b")
_DIFF_X = _DIFF_WRT("x")
_DIFF_Y = _DIFF_WRT("y")
_DIFF_R = _DIFF_WRT("r")
_DIFF_T = _DIFF_WRT(r"(?:theta|th|t|phi|θ)")
_SECOND_T = re.compile(r"diff\([^\n]*,\s*(?:theta|th|t|phi|θ)\s*,\s*2|diff\([^\n]*(?:theta|th|t|phi|θ)\s*,\s*(?:theta|th|t|phi|θ)\)|\.diff\(\s*(?:theta|th|t|phi|θ)\s*,\s*2")
_OVER_R2 = re.compile(r"/\s*\(?\s*r\s*\*\*\s*2|/\s*r\s*\*\s*r\b|/\s*\(\s*r\s*\*\s*r\s*\)|\*\s*r\s*\*\*\s*-2")
_OVER_R = re.compile(r"/\s*r\b(?!\s*\*\*)|\(\s*1\s*/\s*r\s*\)")
_FINITE_DIFF = re.compile(r"\+\s*h\b|-\s*h\b|/\s*h\s*\*\*\s*2|/\s*\(?\s*h\s*\*\s*h|np\.gradient|/\s*\(?\s*2\s*\*\s*h|\beps\b|\bdx\b\s*\*\*\s*2")
_CART_FD = re.compile(r"\(\s*x\s*[+-]\s*h\s*,\s*y|\(\s*x\s*,\s*y\s*[+-]\s*h|\[\s*x\s*[+-]\s*h|np\.gradient\([^)]*,\s*(?:dx|x)\b")
_COMPARE = re.compile(r"==|assert|simplify\(|isclose|allclose|equals\(|abs\(|-\s*\w+\s*\)|print\(")


@dataclass
class CodeAudit:
    code_present: bool
    n_python_blocks: int = 0
    uses_sympy: bool = False
    uses_numpy: bool = False
    uses_plot: bool = False
    verification_type: str = "none"
    verification_types: list[str] = field(default_factory=list)
    has_polar_formula_literal: bool = False
    has_cartesian_reference: bool = False
    circular_verification_candidate: bool = False
    executed: bool | None = None


def _polar_formula_literal(code: str) -> bool:
    """コード中に目標の極座標公式（∂θ² を r² で割る形 + ∂r 項）が書かれているか。"""
    for line_group in _logical_lines(code):
        if (_SECOND_T.search(line_group) or re.search(r"f_?tt|f_?theta_?theta|d2f_?dth", line_group, re.I)) \
                and _OVER_R2.search(line_group) and (_DIFF_R.search(line_group) or _OVER_R.search(line_group)):
            return True
    # 有限差分版: (f(r, t+dt) - 2f + f(r, t-dt)) / (r*r*dt*dt) のような角度 2 階差分
    angle_step = re.search(r"(?:\bt|\bth|theta|phi)\s*[+-]\s*\w+\s*\)", code)
    over_r2 = re.search(r"/\s*\(\s*r\s*\*\s*r\b|/\s*\(?\s*r\s*\*\*\s*2\s*\*", code)
    return bool(angle_step and over_r2)


def _logical_lines(code: str) -> list[str]:
    """括弧が閉じるまでを 1 論理行とする。"""
    out, buf, depth = [], [], 0
    for line in code.splitlines():
        buf.append(line)
        depth += line.count("(") + line.count("[") - line.count(")") - line.count("]")
        if depth <= 0:
            out.append(" ".join(buf))
            buf, depth = [], 0
    if buf:
        out.append(" ".join(buf))
    return out


def audit_code(blocks: list[CodeBlock], exec_log: str | None = None) -> CodeAudit:
    py = [b for b in blocks if b.language in PY_LANGS and _looks_like_python(b.code)]
    if not py:
        return CodeAudit(code_present=bool(blocks), n_python_blocks=0, executed=_executed(exec_log))
    code = "\n".join(b.code for b in py)
    uses_sympy = bool(_SYMPY.search(code))
    uses_numpy = bool(_NUMPY.search(code))
    generic = bool(_GENERIC_FUNC.search(code))
    transform = bool(_POLAR_TRANSFORM.search(code))
    diff_xy = bool(_DIFF_X.search(code) and _DIFF_Y.search(code))
    diff_rt = bool(_DIFF_R.search(code) or _DIFF_T.search(code))
    finite = bool(_FINITE_DIFF.search(code))
    cart_fd = bool(_CART_FD.search(code))
    polar_lit = _polar_formula_literal(code)
    cart_ref = diff_xy or cart_fd or bool(re.search(r"f_?xx|f_?yy|lap_?cart|cartesian", code, re.I))

    types = []
    if uses_sympy and generic and transform and (diff_xy or diff_rt):
        types.append("symbolic_derivation")
    if uses_sympy and (diff_xy or diff_rt) and not generic:
        types.append("symbolic_check")
    if finite or cart_fd or (uses_numpy and re.search(r"np\.(isclose|allclose)", code)):
        types.append("numeric")
    vtype = types[0] if types else "none"
    circular = polar_lit and not cart_ref and vtype != "symbolic_derivation"

    return CodeAudit(
        code_present=True,
        n_python_blocks=len(py),
        uses_sympy=uses_sympy,
        uses_numpy=uses_numpy,
        uses_plot=bool(_PLOT.search(code)),
        verification_type=vtype,
        verification_types=types,
        has_polar_formula_literal=polar_lit,
        has_cartesian_reference=cart_ref,
        circular_verification_candidate=circular,
        executed=_executed(exec_log),
    )


def _looks_like_python(code: str) -> bool:
    return bool(re.search(r"^\s*(import|from|def|print|for|if|[A-Za-z_]\w*\s*=)", code, re.M))


def _executed(exec_log: str | None) -> bool | None:
    if exec_log is None:
        return None
    return bool(exec_log.strip())
