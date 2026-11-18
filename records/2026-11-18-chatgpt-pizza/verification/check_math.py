"""Reproduce the pre-answer checks and the separate check made at registration."""

import sympy as sp


r, theta = sp.symbols("r theta", positive=True)
temperature = sp.Function("T")(r, theta)


def dx(expr):
    return sp.cos(theta) * sp.diff(expr, r) - sp.sin(theta) * sp.diff(expr, theta) / r


def dy(expr):
    return sp.sin(theta) * sp.diff(expr, r) + sp.cos(theta) * sp.diff(expr, theta) / r


def polar_laplacian(expr):
    return sp.diff(r * sp.diff(expr, r), r) / r + sp.diff(expr, theta, 2) / r**2


print("SymPy", sp.__version__)
print("Checks used before the first answer")
identity = sp.simplify(sp.expand(dx(dx(temperature)) + dy(dy(temperature)) - polar_laplacian(temperature)))
radial = sp.simplify(polar_laplacian(r))
balanced = sp.simplify(polar_laplacian(r * sp.cos(theta)))
print("Cartesian minus polar for T(r, theta):", identity)
print("Laplacian of r:", radial)
print("Laplacian of r*cos(theta):", balanced)
assert (identity, radial, balanced) == (0, 1 / r, 0)

# Compare the first illustration with a smooth local example for the later correction.
print("Additional check at registration")
theta0 = sp.symbols("theta0", real=True)
linear = sp.diff(theta, theta, 2) / r**2
cold_middle = sp.diff((theta - theta0)**2, theta, 2) / r**2
radius_ratio = sp.simplify(cold_middle.subs(r, 2 * r) / cold_middle)
print("Angular contribution for a constant angular slope:", linear)
print("Angular contribution for (theta - theta0)**2:", cold_middle)
print("Ratio at twice the radius:", radius_ratio)
assert (linear, cold_middle, radius_ratio) == (0, 2 / r**2, sp.Rational(1, 4))
