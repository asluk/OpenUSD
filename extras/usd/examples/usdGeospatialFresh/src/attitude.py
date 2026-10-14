"""Physical orientation samples follow the proposed quaternion convention."""
import math
import numpy as np
from errors import ResolutionFailure
from geodesy import finite
from interval import reduced,dot_bounds

def multiply(a,b):
    aw,ax,ay,az=a;bw,bx,by,bz=b
    return np.array([aw*bw-ax*bx-ay*by-az*bz,aw*bx+ax*bw+ay*bz-az*by,aw*by-ax*bz+ay*bw+az*bx,aw*bz+ax*by-ay*bx+az*bw])

def from_angles(angles):
    h,p,r=np.array([reduced(a) for a in finite(angles)])*math.pi/180
    qu=np.array([math.cos(h/2),0,0,-math.sin(h/2)])
    qe=np.array([math.cos(p/2),math.sin(p/2),0,0])
    qn=np.array([math.cos(r/2),0,math.sin(r/2),0])
    q=multiply(multiply(qu,qe),qn)
    return q/np.linalg.norm(q)

def matrix(q):
    w,x,y,z=q
    return np.array([[1-2*(y*y+z*z),2*(x*y-w*z),2*(x*z+w*y)],[2*(x*y+w*z),1-2*(x*x+z*z),2*(y*z-w*x)],[2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)]])

def interpolate(a,b,fraction,endpoint_angles=None):
    dot=float(np.dot(a,b))
    if endpoint_angles is None:raise ResolutionFailure('missing-angle-enclosure','Original endpoint angles required for a certified shorter-arc decision')
    lo,hi=dot_bounds(*endpoint_angles)
    uncertainty=max(abs(dot-lo),abs(hi-dot))
    if lo<=0<=hi:
        raise ResolutionFailure('ambiguous-half-turn','No unique shorter physical arc established',angular_uncertainty_radians=2*math.asin(min(1.,uncertainty)),dot_interval=[lo,hi],uncertainty_method='Outward-rounded Taylor enclosure through input angles and Hamilton products')
    if hi<0:b=-b;dot=-dot
    dot=min(1.,dot)
    if dot>0.999999999999:
        q=(1-fraction)*a+fraction*b
    else:
        angle=math.acos(dot)
        q=(math.sin((1-fraction)*angle)*a+math.sin(fraction*angle)*b)/math.sin(angle)
    return q/np.linalg.norm(q)
