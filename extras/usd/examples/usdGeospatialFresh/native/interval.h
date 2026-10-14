// Outward-rounded enclosure of ideal quaternion dots, from authored degrees.
#pragma once
#include <array>
#include <cmath>
#include <algorithm>
#include <limits>
namespace certified {
inline double down(double v){return std::nextafter(v,-INFINITY);}
inline double up(double v){return std::nextafter(v,INFINITY);}
struct I {double lo,hi;I(double v=0):lo(v),hi(v){}I(double a,double b):lo(a),hi(b){}};
inline I operator+(I a,I b){return {down(a.lo+b.lo),up(a.hi+b.hi)};}
inline I operator-(I a){return {-a.hi,-a.lo};}
inline I operator-(I a,I b){return a+(-b);}
inline I operator*(I a,I b){double p[]={a.lo*b.lo,a.lo*b.hi,a.hi*b.lo,a.hi*b.hi};return {down(*std::min_element(p,p+4)),up(*std::max_element(p,p+4))};}
inline I operator/(I a,I b){return a*I(down(1/b.hi),up(1/b.lo));}
inline std::array<I,2> trig(double degrees){
 double pi=3.1415926535897932384626433832795;
 I x=I(std::fmod(degrees,720))*I(down(pi),up(pi))/I(360),s=x,c(1),st=x,ct(1),xx=x*x;
 for(int n=1;n<=32;n++){st=-(st*xx)/I(double(2*n*(2*n+1)));s=s+st;ct=-(ct*xx)/I(double((2*n-1)*(2*n)));c=c+ct;}
 double bound=std::max(std::abs(x.lo),std::abs(x.hi));
 // Every power/product in this positive remainder bound rounds upwards.
 double sr=1,cr=1;for(int n=1;n<=67;n++)sr=up(up(sr*bound)/n);for(int n=1;n<=66;n++)cr=up(up(cr*bound)/n);
 return {s+I(-sr,sr),c+I(-cr,cr)};
}
using Q=std::array<I,4>;
inline Q mul(Q a,Q b){auto w=a[0],x=a[1],y=a[2],z=a[3],v=b[0],i=b[1],j=b[2],k=b[3];return {w*v-x*i-y*j-z*k,w*i+x*v+y*k-z*j,w*j-x*k+y*v+z*i,w*k+x*j-y*i+z*v};}
template<class V>Q quaternion(const V&a){auto h=trig(-a[0]),p=trig(a[1]),r=trig(a[2]);I z(0);return mul(mul(Q{h[1],z,z,h[0]},Q{p[1],p[0],z,z}),Q{r[1],z,r[0],z});}
template<class V>I dot(const V&a,const V&b){auto x=quaternion(a),y=quaternion(b);I result(0);for(int i=0;i<4;i++)result=result+x[i]*y[i];return result;}
}
