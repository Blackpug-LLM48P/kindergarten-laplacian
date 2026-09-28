"""最終式の正誤（ベンチマーク中で唯一「正解」がある項目）。

応答中の数式区間から極座標ラプラシアンの候補式を拾い、SymPy で標準形

    (1/r) ∂_r(r ∂_r f) + (1/r²) ∂_θ² f  =  f_rr + f_r/r + f_θθ/r²

と等価か判定する。説明の良し悪しとは完全に分離する。

LaTeX パーサは latex2sympy2 等に依存せず、この課題で実際に現れる記法
（\\frac{\\partial^2 f}{\\partial r^2}, \\partial_r, f_{rr}, ∂²f/∂θ², 作用素形の ∇² など）に
絞った再帰下降パーサを自前で持つ。外部パーサはバージョンで挙動が変わり、
Layer 1 の「腐りにくさ」を損なうため。

判定:
  correct       最後の候補式が標準形と等価
  incorrect     最後の候補式が標準形と非等価
  unparseable   ラプラシアンらしい数式はあるがどれもパースできない
  absent        候補式が見つからない
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

import sympy as sp

from .textspans import Span, segment

R = sp.Symbol("r", positive=True)
TH = sp.Symbol("theta", real=True)
X = sp.Symbol("x", real=True)
Y = sp.Symbol("y", real=True)
F = sp.Function("f")(R, TH, X, Y)

STANDARD = sp.diff(F, R, 2) + sp.diff(F, R) / R + sp.diff(F, TH, 2) / R**2
CARTESIAN = sp.diff(F, X, 2) + sp.diff(F, Y, 2)

_VARS = {"r": R, "\\theta": TH, "x": X, "y": Y}
_FUNC_WORDS = {"sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "exp": sp.exp, "ln": sp.log, "log": sp.log}


class ParseError(Exception):
    pass


# ---------------------------------------------------------------- 正規化

_UNICODE = [
    ("∂", r" \partial "), ("∇", r" \nabla "), ("Δ", r" \Delta "), ("θ", "\\theta "), ("ϑ", "\\theta "),
    ("φ", "\\phi "), ("ϕ", "\\phi "), ("π", r" \pi "), ("√", r" \sqrt "),
    ("²", "^2"), ("³", "^3"), ("⁻¹", "^{-1}"), ("⁻²", "^{-2}"),
    ("·", "*"), ("⋅", "*"), ("×", "*"), ("−", "-"), ("–", "-"),
    ("（", "("), ("）", ")"), ("＝", "="), ("＋", "+"), ("／", "/"), ("′", "'"),
]


def _strip_braced(s: str, cmd: str, keep: bool) -> str:
    """\\cmd{...} を中身（keep=True）または空に置き換える。入れ子の波括弧に対応。"""
    out, i, n = [], 0, len(cmd)
    while True:
        j = s.find(cmd, i)
        if j < 0 or (j + n < len(s) and s[j + n].isalpha()):
            if j < 0:
                out.append(s[i:])
                break
            out.append(s[i : j + n])
            i = j + n
            continue
        out.append(s[i:j])
        k = j + n
        while k < len(s) and s[k] == " ":
            k += 1
        if k >= len(s) or s[k] != "{":
            i = k
            continue
        depth, m = 0, k
        while m < len(s):
            if s[m] == "{":
                depth += 1
            elif s[m] == "}":
                depth -= 1
                if depth == 0:
                    break
            m += 1
        if keep:
            out.append(" " + s[k + 1 : m] + " ")
        i = m + 1
    return "".join(out)


def _braced_end(s: str, k: int) -> int:
    """s[k] == '{' の対応する '}' の位置。"""
    depth = 0
    for m in range(k, len(s)):
        if s[m] == "{":
            depth += 1
        elif s[m] == "}":
            depth -= 1
            if depth == 0:
                return m
    return len(s) - 1


def _drop_script_group(s: str, cmd: str) -> str:
    """\\underbrace{X}_{注釈} → X。下付き・上付きの注釈を落とす。"""
    while (j := s.find(cmd + "{")) >= 0:
        k = j + len(cmd)
        m = _braced_end(s, k)
        body = s[k + 1 : m]
        rest = s[m + 1 :]
        sm = re.match(r"\s*[_^]\s*", rest)
        if sm and rest[sm.end() : sm.end() + 1] == "{":
            e = _braced_end(rest, sm.end())
            rest = rest[e + 1 :]
        elif sm:
            rest = rest[sm.end() + 1 :]
        s = s[:j] + " {" + body + "} " + rest
    return s


def normalize(src: str) -> str:
    s = src.replace("\\\\", " ")
    for a, b in _UNICODE:
        s = s.replace(a, b)
    for cmd in ("\\underbrace", "\\overbrace"):
        s = _drop_script_group(s, cmd)
    for cmd in ("\\text", "\\textrm", "\\textbf", "\\mbox", "\\tag", "\\label", "\\intertext"):
        s = _strip_braced(s, cmd, keep=False)
    for cmd in ("\\boxed", "\\mathrm", "\\mathit", "\\operatorname", "\\displaystyle", "\\bm", "\\mathbf"):
        s = _strip_braced(s, cmd, keep=True)
    s = re.sub(r"\\color\{[^}]*\}", " ", s)
    s = re.sub(r"\\(begin|end)\{[^}]*\}(\{[^}]*\})?", " ", s)
    s = re.sub(r"\\(left|right|bigl|bigr|Bigl|Bigr|biggl|biggr|big|Big|bigg|Bigg)(?![A-Za-z])\s*([()\[\]|.]|\\\{|\\\})?",
               lambda m: {"\\{": "(", "\\}": ")", ".": ""}.get(m.group(2) or "", m.group(2) or ""), s)
    s = re.sub(r"\\(quad|qquad|,|;|:|!| |displaystyle|limits|nonumber|notag)(?![A-Za-z])", " ", s)
    s = re.sub(r"\\[dt]frac", r"\\frac", s)
    s = s.replace("\\cdot", "*").replace("\\times", "*").replace("\\vartheta", "\\theta")
    s = s.replace("&", " ")
    # 適用条件の注記 (r>0), r \neq 0 を落とす
    s = re.sub(r"[,(]?\s*r\s*(?:>|\\gt|\\neq|\\ne|≠)\s*0\s*\)?", " ", s)
    s = s.replace("\\equiv", "=").replace(":=", "=").replace("\\coloneqq", "=")
    s = re.sub(r"[.,。、;；:：\s]+$", "", s.strip())
    return s


def _angle_is_phi(s: str) -> bool:
    """θ が一度も出ず φ で角度微分している記法なら φ を角度変数とみなす。"""
    return "\\theta" not in s and re.search(r"\\partial\s*\{?\s*\\(var)?phi|_\{?\s*\\(var)?phi", s) is not None


# ---------------------------------------------------------------- 字句解析

@dataclass
class Tok:
    kind: str  # NUM, CMD, LET, SYM, FUNC
    val: str
    space: bool = False  # 直前に空白があったか


def tokenize(s: str) -> list[Tok]:
    toks: list[Tok] = []
    i, space = 0, False
    while i < len(s):
        c = s[i]
        if c.isspace():
            space, i = True, i + 1
            continue
        if c == "\\":
            m = re.match(r"\\([A-Za-z]+|.)", s[i:])
            name = m.group(1)
            if name in ("{", "}"):
                toks.append(Tok("SYM", "(" if name == "{" else ")", space))
            elif name in _FUNC_WORDS:
                toks.append(Tok("FUNC", name, space))
            else:
                toks.append(Tok("CMD", "\\" + name, space))
            i += len(m.group(0))
            if name.isalpha():  # 制御語の直後の空白は区切りにすぎない（LaTeX と同じ）
                while i < len(s) and s[i] in " \t":
                    i += 1
        elif c.isdigit() or (c == "." and i + 1 < len(s) and s[i + 1].isdigit()):
            m = re.match(r"\d*\.?\d+", s[i:])
            toks.append(Tok("NUM", m.group(0), space))
            i += len(m.group(0))
        elif c.isascii() and c.isalpha():
            m = re.match(r"[A-Za-z]+", s[i:])
            run = m.group(0)
            for j, piece in enumerate(re.findall(r"sin|cos|tan|exp|ln|log|.", run)):
                kind = "FUNC" if piece in _FUNC_WORDS else "LET"
                toks.append(Tok(kind, piece, space and j == 0))
            i += len(run)
        elif c in "+-*/^_(){}[]=,|'":
            toks.append(Tok("SYM", c, space))
            i += 1
        else:
            toks.append(Tok("LET", c, space))  # 日本語など: 後で ParseError になる
            i += 1
        space = False
    return toks


# ---------------------------------------------------------------- 構文解析

class Op:
    """被演算子待ちの微分作用素（∂/∂r, ∂_θ² など）。"""

    def __init__(self, var_counts: list[tuple[sp.Symbol, int]]):
        self.var_counts = var_counts

    def apply(self, expr):
        for v, n in self.var_counts:
            expr = sp.diff(expr, v, n)
        return expr


_TERM_END = {"+", "-", "=", ")", "}", "]", ","}


class Parser:
    def __init__(self, toks: list[Tok], func_name: str = "f"):
        self.t = toks
        self.i = 0
        self.func = func_name

    # -- utilities
    def peek(self, k: int = 0) -> Tok | None:
        j = self.i + k
        return self.t[j] if j < len(self.t) else None

    def next(self) -> Tok:
        tok = self.peek()
        if tok is None:
            raise ParseError("unexpected end")
        self.i += 1
        return tok

    def accept(self, kind: str, val: str | None = None) -> Tok | None:
        tok = self.peek()
        if tok and tok.kind == kind and (val is None or tok.val == val):
            self.i += 1
            return tok
        return None

    def expect(self, kind: str, val: str) -> None:
        if not self.accept(kind, val):
            raise ParseError(f"expected {val!r} at {self.i}")

    def at_term_end(self) -> bool:
        tok = self.peek()
        return tok is None or (tok.kind == "SYM" and tok.val in _TERM_END)

    # -- grammar
    def parse(self):
        e = self.expr()
        if self.peek() is not None:
            raise ParseError(f"trailing tokens at {self.i}: {self.peek().val!r}")
        return e

    def expr(self):
        sign = 1
        if self.accept("SYM", "-"):
            sign = -1
        else:
            self.accept("SYM", "+")
        total = sign * self.product()
        while True:
            if self.accept("SYM", "+"):
                total += self.product()
            elif self.accept("SYM", "-"):
                total -= self.product()
            else:
                return total

    def product(self):
        """項（暗黙の積を含む）。作用素が出たら、項の残りをその被演算子にする。"""
        if self.accept("SYM", "-"):
            return -self.product()
        acc = None
        while not self.at_term_end():
            if self.accept("SYM", "*"):
                continue
            divide = bool(self.accept("SYM", "/"))
            f = self.factor()
            if isinstance(f, Op):
                rest = None if self.at_term_end() else self.product()
                f = f.apply(F if rest is None else rest)
                acc = f if acc is None else acc * f
                break
            if divide:
                if acc is None:
                    raise ParseError("leading '/'")
                acc = acc / f
            else:
                acc = f if acc is None else acc * f
        if acc is None:
            raise ParseError(f"empty term at {self.i}")
        return acc

    def factor(self):
        base = self.atom()
        if self.accept("SYM", "^"):
            if isinstance(base, Op):
                raise ParseError("power on operator")
            base = base ** self.script_value()
        if self.peek() and self.peek().kind == "SYM" and self.peek().val == "'":
            raise ParseError("prime notation")
        return base

    def script_value(self):
        tok = self.peek()
        if tok and tok.kind == "SYM" and tok.val in "({":
            return self.group()
        if tok and tok.kind == "NUM":
            self.next()
            # r^23 のような表記は稀。先頭 1 桁だけを指数とみなす（LaTeX と同じ）
            if len(tok.val) > 1 and "." not in tok.val:
                self.t.insert(self.i, Tok("NUM", tok.val[1:]))
                return sp.Integer(tok.val[0])
            return sp.nsimplify(tok.val)
        if tok and tok.kind == "SYM" and tok.val == "-":
            self.next()
            return -self.script_value()
        return self.atom()

    def group(self):
        open_ = self.next().val
        close = {"(": ")", "{": ")", "[": "]"}[open_]
        e = self.expr()
        tok = self.next()
        if tok.val not in (close, "}", ")", "]"):
            raise ParseError(f"unbalanced group at {self.i}")
        return e

    def atom(self):
        tok = self.peek()
        if tok is None:
            raise ParseError("unexpected end")
        if tok.kind == "NUM":
            self.next()
            return sp.nsimplify(tok.val)
        if tok.kind == "SYM" and tok.val in "([{":
            return self.group()
        if tok.kind == "SYM" and tok.val == "|":
            self.next()
            e = self.expr()
            self.expect("SYM", "|")
            return sp.Abs(e)
        if tok.kind == "FUNC":
            self.next()
            fn = _FUNC_WORDS[tok.val]
            power = None
            if self.accept("SYM", "^"):
                power = self.script_value()
            arg = self.factor()
            out = fn(arg)
            return out**power if power is not None else out
        if tok.kind == "CMD":
            return self.command()
        if tok.kind == "LET":
            return self.letter()
        raise ParseError(f"unexpected token {tok.val!r}")

    def command(self):
        tok = self.next()
        name = tok.val
        if name == "\\frac":
            return self.frac()
        if name == "\\partial":
            return self.partial()
        if name == "\\theta":
            return TH
        if name == "\\pi":
            return sp.pi
        if name == "\\sqrt":
            return sp.sqrt(self.factor())
        if name in ("\\nabla", "\\Delta", "\\triangle"):
            raise ParseError("laplacian symbol")
        raise ParseError(f"unsupported command {name}")

    def letter(self):
        tok = self.next()
        v = tok.val
        if v == self.func:
            return self.function_ref()
        if v in ("r", "x", "y"):
            return _VARS[v]
        if v == "e":
            if self.peek() and self.peek().val == "^":
                return sp.E
            return sp.Symbol("e")
        if not (v.isascii() and v.isalpha()):
            raise ParseError(f"unexpected character {v!r}")
        if self.accept("SYM", "_"):
            sub = self.raw_script()
            return sp.Symbol(f"{v}_{sub}")
        return sp.Symbol(v)

    def raw_script(self) -> str:
        tok = self.next()
        if tok.kind == "SYM" and tok.val in "({":
            depth, parts = 1, []
            while depth:
                t = self.next()
                if t.kind == "SYM" and t.val in "({":
                    depth += 1
                elif t.kind == "SYM" and t.val in ")}":
                    depth -= 1
                    if not depth:
                        break
                parts.append(t.val)
            return "".join(parts)
        return tok.val

    def _var_token(self, tok: Tok | None) -> sp.Symbol | None:
        if tok is None:
            return None
        if tok.kind == "LET" and tok.val in ("r", "x", "y"):
            return _VARS[tok.val]
        if tok.kind == "CMD" and tok.val == "\\theta":
            return TH
        return None

    def subscript_vars(self) -> list[sp.Symbol]:
        """f_{rθ} / f_rr / ∂_{rr} の下付き変数列。波括弧なしは空白なしで続く変数を貪欲に読む。"""
        vars_: list[sp.Symbol] = []
        if self.peek() and self.peek().kind == "SYM" and self.peek().val in "({":
            self.next()
            while not (self.peek() and self.peek().kind == "SYM" and self.peek().val in ")}"):
                if self.accept("SYM", ","):
                    continue
                v = self._var_token(self.next())
                if v is None:
                    raise ParseError("non-variable subscript")
                vars_.append(v)
            self.next()
            return vars_
        v = self._var_token(self.next())
        if v is None:
            raise ParseError("non-variable subscript")
        vars_.append(v)
        while (nxt := self._var_token(self.peek())) is not None and not self.peek().space:
            self.next()
            vars_.append(nxt)
        return vars_

    def function_ref(self):
        expr = F
        if self.accept("SYM", "_"):
            for v in self.subscript_vars():
                expr = sp.diff(expr, v)
        self._skip_arglist()
        return expr

    def _skip_arglist(self) -> None:
        """f(r,θ) / f(x, y) の引数並びを読み飛ばす。"""
        tok = self.peek()
        if not (tok and tok.kind == "SYM" and tok.val == "("):
            return
        j, ok = self.i + 1, False
        while j < len(self.t):
            t = self.t[j]
            if t.kind == "SYM" and t.val == ")":
                ok = True
                break
            if not (self._var_token(t) is not None or (t.kind == "SYM" and t.val == ",")):
                return
            j += 1
        if ok:
            self.i = j + 1

    def order(self) -> int:
        if self.accept("SYM", "^"):
            val = self.script_value()
            if not (val.is_Integer and val > 0):
                raise ParseError("bad derivative order")
            return int(val)
        return 1

    def partial(self):
        """\\partial_r..., ∂²f/∂r², ∂/∂θ (\\frac 以外の書き方)。"""
        n, sub = 1, None
        for _ in range(2):
            if self.peek() and self.peek().val == "^":
                n = self.order()
            elif self.accept("SYM", "_"):
                sub = self.subscript_vars()
        if sub is not None:
            if len(sub) == 1:
                return Op([(sub[0], n)])
            return Op([(v, 1) for v in sub])
        # 平文の分数形: ∂[^n] [operand] / ∂v[^k] [∂w[^m]]
        operand = None
        if not (self.peek() and self.peek().val == "/"):
            operand = self.factor()
        self.expect("SYM", "/")
        vc = self.denominator_vars()
        if sum(k for _, k in vc) != n:
            raise ParseError("derivative order mismatch")
        op = Op(vc)
        return op if operand is None else op.apply(operand)

    def denominator_vars(self) -> list[tuple[sp.Symbol, int]]:
        vc = []
        while self.peek() and (self.peek().val == "\\partial" or (self.peek().val == "d" and vc == [])):
            self.next()
            v = self._var_token(self.next())
            if v is None:
                raise ParseError("bad derivative variable")
            vc.append((v, self.order()))
            if not (self.peek() and self.peek().val == "\\partial"):
                break
        if not vc:
            raise ParseError("missing derivative denominator")
        return vc

    def frac(self):
        num = self.brace_tokens()
        den = self.brace_tokens()
        is_d = lambda ts: ts and (ts[0].val == "\\partial" or (ts[0].kind == "LET" and ts[0].val == "d"))
        if is_d(num) and is_d(den):
            sub = Parser(den, self.func)
            vc = sub.denominator_vars()
            if sub.peek() is not None:
                raise ParseError("junk in derivative denominator")
            numer = Parser(num[1:], self.func)
            n = numer.order()
            if sum(k for _, k in vc) != n:
                raise ParseError("derivative order mismatch")
            op = Op(vc)
            if numer.peek() is None:
                return op
            return op.apply(numer.parse())
        return Parser(num, self.func).parse() / Parser(den, self.func).parse()

    def brace_tokens(self) -> list[Tok]:
        tok = self.next()
        if tok.kind == "SYM" and tok.val in "({":
            depth, out = 1, []
            while True:
                t = self.next()
                if t.kind == "SYM" and t.val in "({[":
                    depth += 1
                elif t.kind == "SYM" and t.val in ")}]":
                    depth -= 1
                    if depth == 0:
                        return out
                out.append(t)
        if tok.kind == "NUM" and len(tok.val) > 1:  # \frac12
            self.t.insert(self.i, Tok("NUM", tok.val[1:]))
            return [Tok("NUM", tok.val[0])]
        return [tok]


# ---------------------------------------------------------------- 判定

_GREEK_FUNCS = {"\\Phi": "Φ", "\\Psi": "Ψ", "\\psi": "ψ", "\\chi": "χ", "\\phi": "φ", "\\varphi": "φ"}
_FUNC_LETTER = r"([A-Za-zΦΨψχφ])(?![A-Za-z])"


def prepare(src: str) -> str:
    """正規化 + 角度変数の統一（φ を角度に使う記法）+ ギリシャ文字の関数名を 1 文字に。"""
    s = normalize(src)
    if _angle_is_phi(s):
        s = re.sub(r"\\(var)?phi(?![A-Za-z])", r"\\theta ", s)
    for cmd, ch in _GREEK_FUNCS.items():
        s = re.sub(re.escape(cmd) + r"(?![A-Za-z])\s*", ch, s)
    return s


def _guess_func_name(s: str) -> str:
    cands = re.findall(r"\\partial\s*(?:\^\s*\{?\d\}?)?\s*" + _FUNC_LETTER, s)
    cands += re.findall(r"\\partial\s*_\s*(?:\{[^}]*\}|\\theta|[a-z])\s*(?:\^\s*\{?\d\}?)?\s*" + _FUNC_LETTER, s)
    cands += re.findall(r"(?<![A-Za-z\\])([A-Za-zΦΨψχφ])_\{?\s*(?:r|\\theta|x)", s)
    cands = [c for c in cands if c not in ("r", "x", "y", "d", "e")]
    if not cands:
        return "f"
    return max(set(cands), key=cands.count)


def parse_math(src: str, func_name: str | None = None):
    """1 つの式（等号なし）を SymPy 式にする。失敗時は ParseError。"""
    s = prepare(src)
    return Parser(tokenize(s), func_name or _guess_func_name(s)).parse()


def _deriv_vars(expr) -> set:
    out = set()
    for d in expr.atoms(sp.Derivative):
        out.update(v for v, _ in d.variable_count)
    return out


def _max_order(expr, var) -> int:
    best = 0
    for d in expr.atoms(sp.Derivative):
        for v, n in d.variable_count:
            if v == var:
                best = max(best, int(n))
    return best


def equivalent(a, b, trials: int = 6, seed: int = 29) -> bool:
    """a == b を導関数値・座標をランダムに入れて数値判定（線形でない誤答にも効く）。"""
    d = sp.expand(a - b)
    if d == 0:
        return True
    rng = random.Random(seed)
    atoms = sorted(d.atoms(sp.Derivative), key=sp.default_sort_key)
    for _ in range(trials):
        rep = {atom: sp.Float(rng.uniform(-2, 2)) for atom in atoms}
        rep[F] = sp.Float(rng.uniform(-2, 2))
        val = d.xreplace(rep).subs({R: rng.uniform(0.5, 3), TH: rng.uniform(-3, 3),
                                    X: rng.uniform(-2, 2), Y: rng.uniform(-2, 2)})
        try:
            v = complex(sp.N(val))
        except (TypeError, ValueError):
            return False
        if abs(v) > 1e-8:
            return False
    return True


# Δθ・Δr のような「小さな変化」は除く
_LAP_MARKER = re.compile(
    r"\\nabla|∇|\\triangle|ラプラシアン|[Ll]aplacian"
    r"|(?:\\Delta|Δ)(?!\s*(?:\\theta|θ|\\phi|\\varphi|φ|[rxystAhV](?![A-Za-z])))"
)


@dataclass
class Candidate:
    offset: int
    source: str
    status: str  # correct / incorrect / unparseable
    expr: str | None = None


@dataclass
class FormulaResult:
    status: str
    n_candidates: int = 0
    n_unparseable: int = 0
    any_incorrect: bool = False
    first_pos: float | None = None
    last_pos: float | None = None
    position: str | None = None  # head / middle / tail（初出位置）
    final_expr: str | None = None
    candidates: list[Candidate] = field(default_factory=list)


def _classify_part(expr) -> str:
    dv = _deriv_vars(expr)
    if expr.free_symbols - {R, TH, X, Y}:
        return "other"
    if not dv:
        return "none"
    if dv & {X, Y} and not dv & {R, TH}:
        return "cart"
    if dv & {R, TH} and not dv & {X, Y}:
        return "polar"
    return "mixed"


def check_equation(src: str) -> tuple[str, str | None] | None:
    """等式 1 本を判定。候補でなければ None。"""
    norm_all = prepare(src)
    func = _guess_func_name(norm_all)
    marker = bool(_LAP_MARKER.search(src))
    raw_parts = [p for p in re.split(r"(?<![<>!])=(?!=)", norm_all) if p.strip()]
    parsed = []
    failed = False
    for part in raw_parts:
        if _LAP_MARKER.search(part):
            continue  # 左辺の ∇²f / Δf
        try:
            parsed.append(parse_math(part, func))
        except (ParseError, sp.SympifyError, TypeError, ValueError, ZeroDivisionError, AttributeError, KeyError):
            failed = True
    kinds = [_classify_part(e) for e in parsed]
    for e, k in zip(parsed, kinds):
        if k == "cart" and not equivalent(e, CARTESIAN):
            return None  # f_x = ... のような途中式
        if k == "cart":
            marker = True
    polar = [e for e, k in zip(parsed, kinds) if k == "polar"]
    if not marker:
        polar = [e for e in polar if _max_order(e, TH) >= 2 and _max_order(e, R) >= 2]
    if not polar:
        if failed and marker and ("\\theta" in norm_all or "\\phi" in norm_all):
            return ("unparseable", None)
        return None
    ok = all(equivalent(e, STANDARD) for e in polar)
    return ("correct" if ok else "incorrect", str(polar[-1]))


_PLAIN_CHARS = r"A-Za-z0-9 \t∂∇Δθφ²³⁻¹·()+\-*/^_{}\\.,'′|\[\]"
_PLAIN_FORMULA = re.compile(rf"[{_PLAIN_CHARS}]*=[{_PLAIN_CHARS}=]*")
_TRAILING_WORDS = re.compile(r"(?<=[^A-Za-z\\])\s+(?!(?:sin|cos|tan|exp|ln|log)\b)[A-Za-z]{3,}\b.*$")


def _plain_segments(sp_: Span) -> list[tuple[int, str]]:
    """散文・インラインコード中の平文の式（∇²f = f_rr + (1/r)f_r ...）を拾う。"""
    out = []
    for m in _PLAIN_FORMULA.finditer(sp_.text):
        seg = m.group(0).strip()
        if not ("=" in seg and ("∂" in seg or "_" in seg) and ("θ" in seg or "theta" in seg or "φ" in seg)):
            continue
        eq = seg.index("=")
        seg = seg[:eq] + _TRAILING_WORDS.sub("", seg[eq:])
        out.append((sp_.start + m.start(), seg))
    return out


def _split_lines(src: str) -> list[str]:
    """\\\\ で区切られた行を独立した式に分ける。'&=' や '+' で始まる行は前の行の続き。"""
    lines: list[str] = []
    for ln in re.split(r"\\\\", src):
        ln = re.sub(r"^\s*\[[^\]]*\]", "", ln)  # \\[2mm] の行間指定
        if not ln.strip():
            continue
        if lines and re.match(r"\s*&?\s*[=+\-]", ln):
            lines[-1] += " " + ln
        else:
            lines.append(ln)
    return lines


def formula_candidates(text: str, spans: list[Span] | None = None) -> list[Candidate]:
    spans = spans if spans is not None else segment(text)
    segs: list[tuple[int, str]] = []
    for s in spans:
        if s.kind == "math":
            segs.append((s.start, s.text))
        elif s.kind in ("prose", "inline_code") or (s.kind == "code" and s.lang in ("", "text", "plaintext", "txt")):
            segs.extend(_plain_segments(s))
    cands = []
    for off, src in segs:
        for piece in _split_lines(src):
            res = check_equation(piece)
            if res is not None:
                cands.append(Candidate(off, piece.strip(), res[0], res[1]))
    return cands


def _bucket(pos: float) -> str:
    return "head" if pos < 1 / 3 else ("middle" if pos < 2 / 3 else "tail")


def check_formula(text: str, spans: list[Span] | None = None) -> FormulaResult:
    cands = formula_candidates(text, spans)
    if not cands:
        return FormulaResult("absent")
    n = max(len(text), 1)
    parsed = [c for c in cands if c.status != "unparseable"]
    unparse = len(cands) - len(parsed)
    first = cands[0].offset / n
    if not parsed:
        return FormulaResult("unparseable", len(cands), unparse, False, first, cands[-1].offset / n,
                             _bucket(first), None, cands)
    final = parsed[-1]
    return FormulaResult(
        status=final.status,
        n_candidates=len(cands),
        n_unparseable=unparse,
        any_incorrect=any(c.status == "incorrect" for c in parsed),
        first_pos=parsed[0].offset / n,
        last_pos=final.offset / n,
        position=_bucket(parsed[0].offset / n),
        final_expr=final.expr,
        candidates=cands,
    )
