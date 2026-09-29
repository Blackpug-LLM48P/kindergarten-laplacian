"""評価者による追加検算（回答本文とは別）。

1. 回答の laplacian() を、角度項が作動する関数で直交座標の中央差分・解析解と照合する。
   回答本文の手計算 u=r^2 は角度項がゼロになるため、その穴を埋める。
2. 切れ端（扇形の輪の一部）の面積が r*h*k とぴったり一致するという本文の主張を SymPy で確認する。

回答が主張する「5種類・計45点、最大絶対誤差 約3.4e-7」はコードが示されていないため再現対象にしていない。
"""

import math

import sympy as sp

from answer_code import laplacian

CASES = [
    ("x^2+y^2 = r^2", lambda x, y: x * x + y * y, lambda x, y: 4.0),
    ("x^2-y^2 = r^2 cos2θ", lambda x, y: x * x - y * y, lambda x, y: 0.0),
    ("x^3-3xy^2 = r^3 cos3θ", lambda x, y: x**3 - 3 * x * y * y, lambda x, y: 0.0),
    ("x^3-xy^2", lambda x, y: x**3 - x * y * y, lambda x, y: 4 * x),
    ("exp(0.2x)cos(0.3y)", lambda x, y: math.exp(0.2 * x) * math.cos(0.3 * y),
     lambda x, y: -0.05 * math.exp(0.2 * x) * math.cos(0.3 * y)),
]
POINTS = [(0.4, 0.3), (1.2, 1.8), (2.0, -0.7), (3.1, 2.9)]


def cart_lap(F, x, y, h):
    return (F(x + h, y) + F(x - h, y) + F(x, y + h) + F(x, y - h) - 4 * F(x, y)) / h**2


def polar(F):
    return lambda r, t: F(r * math.cos(t), r * math.sin(t))


print("1) 回答の laplacian() と解析解・直交座標の中央差分の比較")
for h in (1e-2, 1e-3, 1e-4):
    err_exact = err_cart = 0.0
    for _, F, exact in CASES:
        for r, t in POINTS:
            x, y = r * math.cos(t), r * math.sin(t)
            got = laplacian(polar(F), r, t, h)
            err_exact = max(err_exact, abs(got - exact(x, y)))
            err_cart = max(err_cart, abs(got - cart_lap(F, x, y, 1e-3)))
    print(f"h={h:g}: 5関数×4地点=20件  最大誤差 対解析解 {err_exact:.2e} / 対直交座標差分(h=1e-3) {err_cart:.2e}")

print("2) 切れ端の面積")
r, h, k = sp.symbols("r h k", positive=True)
area = sp.Rational(1, 2) * k * ((r + h / 2) ** 2 - (r - h / 2) ** 2)
print("1/2·k·((r+h/2)^2-(r-h/2)^2) =", sp.simplify(area))
