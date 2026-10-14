from pathlib import Path
import sys,math
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from interval import dot_bounds
from queries import relative_frame
from fixtures import stage,bind,wkt
from scene import Reader
from errors import ResolutionFailure

def test_interval_quaternion_dot_contains_high_precision_oracle():
 from decimal import Decimal as D,getcontext
 getcontext().prec=100
 pi=D('3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679')
 def trig(degrees):
  x=(D.from_float(float(degrees))%720)*pi/360
  sine=x;cosine=D(1);st=x;ct=D(1);n=0
  while True:
   n+=1;st=-st*x*x/((2*n)*(2*n+1));ct=-ct*x*x/((2*n-1)*(2*n));sine+=st;cosine+=ct
   if abs(st)<D('1e-90') and abs(ct)<D('1e-90'):break
  return sine,cosine
 def mul(a,b):
  w,x,y,z=a;v,i,j,k=b
  return [w*v-x*i-y*j-z*k,w*i+x*v+y*k-z*j,w*j-x*k+y*v+z*i,w*k+x*j-y*i+z*v]
 def q(a):
  sh,ch=trig(a[0]);sp,cp=trig(a[1]);sr,cr=trig(a[2])
  return mul(mul([ch,0,0,-sh],[cp,sp,0,0]),[cr,0,sr,0])
 rng=np.random.default_rng(64102)
 cases=[((0,0,0),(180,0,0)),((0,0,0),(180-1e-10,0,0)),((0,0,0),(180+1e-10,0,0)),((0,0,0),(360,0,0)),((1e15,-1e15,1e15),(1e15+180,-1e15,1e15))]
 cases += [(rng.uniform(-720,720,3),rng.uniform(-720,720,3)) for _ in range(100)]
 for a,b in cases:
  lo,hi=dot_bounds(a,b);reference=sum(x*y for x,y in zip(q(a),q(b)))
  assert D.from_float(lo)<=reference<=D.from_float(hi),(a,b,lo,reference,hi)

def test_relative_frame_and_singular_inverse():
 s=stage();bind(s,'/World/A',orientation=(0,0,0));bind(s,'/World/B',orientation=(90,0,0))
 r=relative_frame(s,'/World/A','/World/B',wkt(4978))
 np.testing.assert_allclose(r['linear_from_to'],[[0,-1,0],[1,0,0],[0,0,1]],atol=1e-8)
 from pxr import UsdGeom
 UsdGeom.Xformable(s.GetPrimAtPath('/World/B')).AddScaleOp().Set((0,1,1))
 with pytest.raises(ResolutionFailure,match='singular-required-inverse'):relative_frame(s,'/World/A','/World/B',wkt(4978))
