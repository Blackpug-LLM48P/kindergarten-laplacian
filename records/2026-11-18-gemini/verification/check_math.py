import sympy as sp

# 1. 変数と関数の準備（r: まっすぐの距離, theta: 角度）
r, theta = sp.symbols("r theta", real=True, positive=True)
f = sp.Function("f")(r, theta)

# 2. 極座標と直交座標(x, y)のルールだけを教える
x = r * sp.cos(theta)
y = r * sp.sin(theta)

# 3. ヤコビ行列 J を作って逆行列をとる（∂r/∂x, ∂r/∂y, ∂θ/∂x, ∂θ/∂y を自動計算！）
J = sp.Matrix(
    [[sp.diff(x, r), sp.diff(x, theta)], [sp.diff(y, r), sp.diff(y, theta)]]
)
J_inv = sp.trigsimp(J.inv())

dr_dx, dr_dy = J_inv[0, 0], J_inv[0, 1]
dtheta_dx, dtheta_dy = J_inv[1, 0], J_inv[1, 1]

print("--- 1階微分の変換パーツ（Pythonが自動導出） ---")
print(f"∂r/∂x = {dr_dx},  ∂r/∂y = {dr_dy}")
print(f"∂θ/∂x = {dtheta_dx}, ∂θ/∂y = {dtheta_dy}\n")


# 4. x方向の微分 (∂/∂x) と y方向の微分 (∂/∂y) を関数にする
def d_dx(expr):
  return dr_dx * sp.diff(expr, r) + dtheta_dx * sp.diff(expr, theta)


def d_dy(expr):
  return dr_dy * sp.diff(expr, r) + dtheta_dy * sp.diff(expr, theta)


# 5. ワッフルのラプラシアン Δf = ∂²f/∂x² + ∂²f/∂y² を計算して整理！
laplacian_polar = sp.expand(sp.trigsimp(d_dx(d_dx(f)) + d_dy(d_dy(f))))

print("--- 完成した極座標ラプラシアン ---")
sp.pprint(laplacian_polar)

# Registration checks. The answer's code ends at sp.pprint above.
print("Registration environment: SymPy", sp.__version__)
expected = sp.diff(f, r, 2) + sp.diff(f, r) / r + sp.diff(f, theta, 2) / r**2
residual = sp.simplify(laplacian_polar - expected)
print("General identity residual:", residual)
assert residual == 0

for expr, target in [(r, 1 / r), (r**2, 4), (r * sp.cos(theta), 0)]:
    value = sp.simplify(laplacian_polar.subs(f, expr).doit())
    print(f"Laplacian of {expr}: {value}")
    assert sp.simplify(value - target) == 0
