import math

def cart_lap(F,x,y,h):
    return (F(x+h,y)+F(x-h,y)+F(x,y+h)+F(x,y-h)-4*F(x,y))/h**2

def polar_lap(F,r,t,h):
    f=lambda rr,tt:F(rr*math.cos(tt),rr*math.sin(tt))
    dt=h/r
    radial=(f(r+h,t)-2*f(r,t)+f(r-h,t))/h**2
    extra=(f(r+h,t)-f(r-h,t))/(2*h*r)
    angular=(f(r,t+dt)-2*f(r,t)+f(r,t-dt))/(r*r*dt*dt)
    return radial+extra+angular, radial+angular, (radial,extra,angular)

cases=[('bowl r^2',lambda x,y:x*x+y*y,lambda x,y:4.0),
('plane x',lambda x,y:x,lambda x,y:0.0),
('saddle x*y',lambda x,y:x*y,lambda x,y:0.0),
('exp*cos',lambda x,y:math.exp(.2*x)*math.cos(.3*y),
lambda x,y:-.05*math.exp(.2*x)*math.cos(.3*y))]
print('At r=2, theta=0, step=0.001')
for name,F,exact in cases:
    result,missing,parts=polar_lap(F,2,0,1e-3)
    print(f'{name:12} Cartesian={cart_lap(F,2,0,1e-3): .8f}; polar={result: .8f}; without extra={missing: .8f}; terms={tuple(round(v,8) for v in parts)}')
points=[(.4,.3),(1.2,1.8),(2.0,-.7),(3.1,2.9)]
for h in [1e-2,1e-3]:
    error=0
    for _,F,exact in cases:
        for r,t in points:
            x,y=r*math.cos(t),r*math.sin(t)
            got=polar_lap(F,r,t,h)[0]
            error=max(error,abs(got-exact(x,y)))
    print(f'h={h}: maximum polar-vs-analytic error over 16 cases = {error:.3e}')
print('Geometry: outward displacement of straight tangent endpoints')
for h in [1,.1,.01]:
    r=2
    dr=h*h/(math.hypot(r,h)+r)
    print(f'h={h}: delta_r={dr:.10f}, delta_r/h^2={dr/(h*h):.10f}; limit=1/(2r)=0.25')
