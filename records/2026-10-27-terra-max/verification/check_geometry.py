"""Check the finite-cell algebra exactly; this is not a general proof."""
from fractions import Fraction as F

def u(r, theta):
    # A smooth local polar-coordinate example; not periodic across a branch cut.
    return r*r + 3*r*theta + 2*theta*theta

def check(r, theta, a, b):
    assert r > a/2 > 0 and b > 0
    center = u(r, theta)
    outer, inner = u(r+a, theta), u(r-a, theta)
    right, left = u(r, theta+b), u(r, theta-b)
    area = r*a*b
    radial_flux = (r+a/2)*b*(outer-center)/a + (r-a/2)*b*(inner-center)/a
    angular_flux = a*((right-center)+(left-center))/(r*b)
    geometric_stencil = (radial_flux+angular_flux)/area
    expanded_stencil = ((outer-2*center+inner)/a**2
                        + (outer-inner)/(2*r*a)
                        + (right-2*center+left)/(r*r*b*b))
    # Analytic result for this particular quadratic u: u_rr + u_r/r + u_tt/r².
    analytic = 4 + 3*theta/r + 4/(r*r)
    assert geometric_stencil == expanded_stencil == analytic
    print(f"r={r}, theta={theta}, a={a}, b={b}: exact={analytic} PASS")

for args in [(F(2), F(1,4), F(1,2), F(1,10)),
             (F(1), F(1,8), F(1,4), F(1,20)),
             (F(3), F(1,5), F(1,3), F(1,30))]:
    check(*args)
print("PASS: 3 exact rational cases; local finite-cell stencil only")
