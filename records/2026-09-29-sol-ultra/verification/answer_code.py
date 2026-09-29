def laplacian(u, r, theta, h=1e-4):
    center = u(r, theta)
    radial = (
        u(r+h, theta) - 2*center + u(r-h, theta)
    ) / h**2
    widening = (
        u(r+h, theta) - u(r-h, theta)
    ) / (2*h*r)
    angular = (
        u(r, theta+h) - 2*center + u(r, theta-h)
    ) / (r*r*h*h)
    return radial + widening + angular
print(round(laplacian(lambda r, theta: r*r, 2, 0.7), 6))
# 4.0
