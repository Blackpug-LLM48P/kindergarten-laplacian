import math
cases=[('r²',lambda r,t:r*r,lambda x,y:x*x+y*y,lambda x,y:4),('x',lambda r,t:r*math.cos(t),lambda x,y:x,lambda x,y:0),('x(x²+y²)',lambda r,t:r**3*math.cos(t),lambda x,y:x*(x*x+y*y),lambda x,y:8*x),('x²y²',lambda r,t:r**4*math.cos(t)**2*math.sin(t)**2,lambda x,y:x*x*y*y,lambda x,y:2*(x*x+y*y)),('r',lambda r,t:r,lambda x,y:math.hypot(x,y),lambda x,y:1/math.hypot(x,y)),('x²-y²',lambda r,t:r*r*math.cos(2*t),lambda x,y:x*x-y*y,lambda x,y:0)]
h=1e-4
for name,pf,cf,truth in cases:
 r,t=2.0,0.7
 x,y=r*math.cos(t),r*math.sin(t)
 center=pf(r,t)
 first=(pf(r+h,t)-pf(r-h,t))/(2*h)
 second=(pf(r+h,t)-2*center+pf(r-h,t))/h**2
 angular=(pf(r,t+h)-2*center+pf(r,t-h))/h**2
 polar=second+first/r+angular/r**2
 true=truth(x,y)
 print(f'{name:10} polar={polar: .9f} exact={true: .9f} abs error={abs(polar-true):.2g}')
