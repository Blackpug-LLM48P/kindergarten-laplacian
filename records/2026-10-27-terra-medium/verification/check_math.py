"""Independent polar-Laplacian checks; Python standard library only.

The formal calculation starts from Cartesian chain-rule operators, not
the polar formula under test. Its coefficients are small dyadic complex
numbers, exactly representable by Python's binary floating-point type.
Numerical checks and quadrature have explicit, separate tolerances.
Run with ordinary Python (do not use -O, which disables assertions).
"""
import math
from collections import defaultdict


# Terms: r**n * exp(i*k*theta) * partial_r**a partial_theta**b u.
def add(*expressions):
    out = defaultdict(complex)
    for expression in expressions:
        for key, coefficient in expression.items():
            out[key] += coefficient
    return {key: value for key, value in out.items() if value != 0}


def derivative(expression, axis):
    out = defaultdict(complex)
    for (n, k, a, b), coefficient in expression.items():
        if axis == "r":
            out[n - 1, k, a, b] += n * coefficient
            out[n, k, a + 1, b] += coefficient
        else:
            out[n, k, a, b] += 1j * k * coefficient
            out[n, k, a, b + 1] += coefficient
    return {key: value for key, value in out.items() if value != 0}


def multiply(expression, terms):
    out = defaultdict(complex)
    for (n, k, a, b), coefficient in expression.items():
        for nr, kt, value in terms:
            out[n + nr, k + kt, a, b] += coefficient * value
    return {key: value for key, value in out.items() if value != 0}


def dx(expression):
    # cos(theta) d_r - sin(theta)/r d_theta
    return add(
        multiply(derivative(expression, "r"), [(0, 1, .5), (0, -1, .5)]),
        multiply(derivative(expression, "t"), [(-1, 1, .5j), (-1, -1, -.5j)]),
    )


def dy(expression):
    # sin(theta) d_r + cos(theta)/r d_theta
    return add(
        multiply(derivative(expression, "r"), [(0, 1, -.5j), (0, -1, .5j)]),
        multiply(derivative(expression, "t"), [(-1, 1, .5), (-1, -1, .5)]),
    )


u = {(0, 0, 0, 0): 1}
actual = add(dx(dx(u)), dy(dy(u)))
expected = {(0, 0, 2, 0): 1, (-1, 0, 1, 0): 1, (-2, 0, 0, 2): 1}
assert actual == expected, (actual, expected)
print("Formal Cartesian chain-rule expansion:", actual)
print("General identity residual: zero")

# Polar finite differences versus independently specified Cartesian derivatives.
cases = [
    ("constant", lambda x, y: 3, lambda x, y: 0),
    ("plane", lambda x, y: x + 2*y, lambda x, y: 0),
    ("bowl", lambda x, y: x*x + y*y, lambda x, y: 4),
    ("saddle", lambda x, y: x*x - y*y, lambda x, y: 0),
    ("quartic minimum", lambda x, y: x**4 + y**4,
     lambda x, y: 12*(x*x + y*y)),
    ("mixed polynomial", lambda x, y: x**3*y*y + 2*x*y + y**4,
     lambda x, y: 6*x*y*y + 2*x**3 + 12*y*y),
    ("nonpolynomial", lambda x, y: math.exp(x) + math.sin(y),
     lambda x, y: math.exp(x) - math.sin(y)),
]
points = [(.7, .3), (1.2, 1.1), (2., -1.)]
h = 1e-4
for name, function, laplacian in cases:
    worst = 0
    for radius, theta in points:
        def g(rr, tt):
            return function(rr * math.cos(tt), rr * math.sin(tt))

        estimate = (
            (g(radius+h, theta) - 2*g(radius, theta) + g(radius-h, theta))/h**2
            + (g(radius+h, theta) - g(radius-h, theta))/(2*h*radius)
            + (g(radius, theta+h) - 2*g(radius, theta) + g(radius, theta-h))
            / (h*h*radius*radius)
        )
        reference = laplacian(radius*math.cos(theta), radius*math.sin(theta))
        worst = max(worst, abs(estimate - reference))
    print(name, "max absolute error:", format(worst, ".3g"))
    assert worst < 1e-4


def simpson(function, left, right, n=600):
    step = (right-left)/n
    return step/3 * (
        function(left) + function(right)
        + 4*sum(function(left+i*step) for i in range(1, n, 2))
        + 2*sum(function(left+i*step) for i in range(2, n, 2))
    )


# Boundary flux for u=r^4+r^2*cos(2theta)+r*sin(theta).
# Cartesian u=(x^2+y^2)^2+x^2-y^2+y, so Delta u=16*(x^2+y^2).
ur = lambda r, t: 4*r**3 + 2*r*math.cos(2*t) + math.sin(t)
ut = lambda r, t: -2*r*r*math.sin(2*t) + r*math.cos(t)
a, b, c, d = 1., 2., 0., math.pi/3
flux = (
    simpson(lambda t: b*ur(b, t)-a*ur(a, t), c, d)
    + simpson(lambda r: (ut(r, d)-ut(r, c))/r, a, b)
)
area_integral = 20*math.pi
print("Finite-sector flux:", flux, "analytic area integral:", area_integral,
      "residual:", abs(flux-area_integral))
assert abs(flux-area_integral) < 1e-8
print("Strict minimum u=x^4+y^4: u(0,0)=0; u>0 elsewhere; Laplacian(0,0)=0.")
print("PASS: generic formal identity, 21 numerical point checks, finite-sector flux.")
