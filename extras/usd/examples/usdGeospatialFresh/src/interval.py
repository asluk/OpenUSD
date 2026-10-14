"""Outward-rounded arithmetic for the exact input-angle quaternion dot product."""
import math
from fractions import Fraction

def down(v):return math.nextafter(v,-math.inf)
def up(v):return math.nextafter(v,math.inf)

class Interval:
    def __init__(self,lo,hi=None):self.lo=float(lo);self.hi=float(lo if hi is None else hi)
    def __add__(self,b):
        b=b if isinstance(b,Interval) else Interval(b)
        return Interval(down(self.lo+b.lo),up(self.hi+b.hi))
    __radd__=__add__
    def __neg__(self):return Interval(-self.hi,-self.lo)
    def __sub__(self,b):return self+-b if isinstance(b,Interval) else self+(-b)
    def __mul__(self,b):
        b=b if isinstance(b,Interval) else Interval(b)
        p=[self.lo*b.lo,self.lo*b.hi,self.hi*b.lo,self.hi*b.hi]
        return Interval(down(min(p)),up(max(p)))
    __rmul__=__mul__
    def __truediv__(self,b):
        b=b if isinstance(b,Interval) else Interval(b)
        if b.lo<=0<=b.hi:raise ArithmeticError('Interval divisor crosses zero')
        return self*Interval(down(1/b.hi),up(1/b.lo))

def reduced(angle):
    f=Fraction.from_float(float(angle))
    sign=-1 if f<0 else 1;f=abs(f)
    if f>=720:f=f-Fraction(f//720)*720
    return float(sign*f)

def trig(angle):
    x=Interval(reduced(angle))*Interval(down(math.pi),up(math.pi))/360
    square=x*x
    sine=x;term=x;cosine=Interval(1);cterm=Interval(1)
    for n in range(1,33):
        term=-(term*square)/((2*n)*(2*n+1));sine=sine+term
        cterm=-(cterm*square)/((2*n-1)*(2*n));cosine=cosine+cterm
    bound=max(abs(x.lo),abs(x.hi))
    sr=up(bound**67/math.factorial(67));cr=up(bound**66/math.factorial(66))
    return sine+Interval(-sr,sr),cosine+Interval(-cr,cr)

def multiply(a,b):
    w,x,y,z=a;v,i,j,k=b
    return [w*v-x*i-y*j-z*k,w*i+x*v+y*k-z*j,w*j-x*k+y*v+z*i,w*k+x*j-y*i+z*v]

def quaternion(angles):
    sh,ch=trig(-angles[0]);sp,cp=trig(angles[1]);sr,cr=trig(angles[2]);zero=Interval(0)
    return multiply(multiply([ch,zero,zero,sh],[cp,sp,zero,zero]),[cr,zero,sr,zero])

def dot_bounds(a,b):
    qa,qb=quaternion(a),quaternion(b);total=Interval(0)
    for x,y in zip(qa,qb):total=total+x*y
    return total.lo,total.hi
