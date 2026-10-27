import math
h = 1e-4

def polar_lap(f, r, t):
    mid = f(r, t)
    radial_second = (f(r+h,t) - 2*mid + f(r-h,t)) / h**2
    radial_first = (f(r+h,t) - f(r-h,t)) / (2*h)
    angular_second = (f(r,t+h) - 2*mid + f(r,t-h)) / h**2
    return radial_second + radial_first/r + angular_second/r**2

def cart_lap(f, x, y):
    mid = f(x,y)
    return (f(x+h,y)-2*mid+f(x-h,y)+f(x,y+h)-2*mid+f(x,y-h))/h**2

examples = [
 ('r²', lambda r,t:r*r, lambda x,y:x*x+y*y, lambda r,t:4),
 ('r cosθ', lambda r,t:r*math.cos(t), lambda x,y:x, lambda r,t:0),
 ('r³ cosθ', lambda r,t:r**3*math.cos(t), lambda x,y:x*(x*x+y*y), lambda r,t:8*r*math.cos(t)),
 ('r⁴ cos²θ sin²θ', lambda r,t:r**4*math.cos(t)**2*math.sin(t)**2, lambda x,y:x*x*y*y, lambda r,t:2*r*r),
]
points = [(0.7,2.0),(2.0,0.7),(3.0,-1.5)]
max_error=0.0
for name,pf,cf,exact in examples:
 for r,t in points:
  x,y=r*math.cos(t),r*math.sin(t)
  a,b,c=polar_lap(pf,r,t),cart_lap(cf,x,y),exact(r,t)
  err=max(abs(a-c),abs(b-c))
  max_error=max(max_error,err)
  print(f'{name:16} r={r:.1f} θ={t:4.1f} polar={a:.7f} Cartesian={b:.7f} exact={c:.7f} max_error={err:.2g}')
assert max_error < 1e-5, max_error
print(f'PASS: 12 cases; maximum absolute error {max_error:.2g}')
