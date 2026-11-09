"""Check used by the answer: Cartesian Laplacian minus the polar formula.

Same expressions as the inline `python3 -c` run made while answering,
saved as a file so it can be re-run. Requires SymPy.
"""
import sympy as sp

r, t = sp.symbols('r theta', positive=True)
x, y = sp.symbols('x y', real=True)
tests = [
    x**3*y - 2*x*y**2 + x**2,
    sp.exp(x)*sp.sin(y),
    sp.exp(-(x**2 + y**2))*x,
    sp.log(x**2 + y**2),
]
polar = {x: r*sp.cos(t), y: r*sp.sin(t)}

print("sympy", sp.__version__)
for F in tests:
    cart = (sp.diff(F, x, 2) + sp.diff(F, y, 2)).subs(polar)
    f = F.subs(polar)
    pol = sp.diff(r*sp.diff(f, r), r)/r + sp.diff(f, t, 2)/r**2
    residual = sp.simplify(cart - pol)
    print(F, "->", residual)
    assert residual == 0
print("PASS: 4 functions, residual 0")
