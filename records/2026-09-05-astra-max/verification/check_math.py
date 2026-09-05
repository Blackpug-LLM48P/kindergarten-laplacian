"""Reconstructed from the visible benchmark command; Python stdlib only."""
import math

cases = [
    ('x', lambda r, a: r * math.cos(a), lambda r, a: 0.),
    ('radius', lambda r, a: r, lambda r, a: 1 / r),
    ('radius_squared', lambda r, a: r * r, lambda r, a: 4.),
    ('y_squared', lambda r, a: r * r * math.sin(a) ** 2, lambda r, a: 2.),
]
h = 1e-4
for name, f, target in cases:
    errors = []
    for r in [.7, 1.4, 3.2]:
        for a in [.2, 1.1, 2.4]:
            radial2 = (f(r + h, a) - 2 * f(r, a) + f(r - h, a)) / (h * h)
            radial1 = (f(r + h, a) - f(r - h, a)) / (2 * h * r)
            angle2 = (f(r, a + h) - 2 * f(r, a) + f(r, a - h)) / (r * r * h * h)
            errors.append(abs(radial2 + radial1 + angle2 - target(r, a)))
    error = max(errors)
    assert error < 2e-6, (name, error)
    print(name, 'passed; max error', f'{error:.2g}')

for r in [2, 3, 4]:
    inner, outer = r - 1, r + 1
    area = (outer * outer - inner * inner) / 2
    assert abs((outer - inner) / area - 1 / r) < 1e-12
print('sector geometry: passed')
