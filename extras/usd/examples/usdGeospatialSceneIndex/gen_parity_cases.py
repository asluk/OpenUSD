#!/usr/bin/env python3
"""
gen_parity_cases.py -- emit the parity test cases for the C++ GeoCrsEngine.

Each line: name \t srcWkt \t x \t y \t z \t gtX \t gtY \t gtZ
  (x,y,z) follow the axis-order contract (lon/E, lat/N, h).
  (gtX,gtY,gtZ) = closed-form WGS84 geodesy ECEF of the authored point
                  (INDEPENDENT of PROJ -- the non-circular oracle).

The datasets mirror generalization_suite.py exactly: geographic Earth-2-like
points + 5 projected benchmarks (UTM N/S, NZTM, equatorial, high-lat). For
projected datasets the authored (E,N,h) is produced by forward-projecting the
published lon/lat, but correctness is judged against cf_ecef(lon,lat,h), so a
wrong projection/axis order cannot pass.
"""
import sys, numpy as np
from pyproj import CRS, Transformer

_A = 6378137.0
_F = 1.0/298.257223563
_E2 = _F*(2.0-_F)

def cf_ecef(lon, lat, h=0.0):
    lam = np.radians(lon); phi = np.radians(lat)
    N = _A/np.sqrt(1.0-_E2*np.sin(phi)**2)
    return np.array([(N+h)*np.cos(phi)*np.cos(lam),
                     (N+h)*np.cos(phi)*np.sin(lam),
                     (N*(1.0-_E2)+h)*np.sin(phi)])

def wkt(epsg):
    return CRS.from_epsg(epsg).to_wkt(version="WKT2_2019")

def proj_en(lon, lat, h, epsg):
    t = Transformer.from_crs(CRS.from_epsg(4979), CRS.from_epsg(epsg), always_xy=True)
    return t.transform(lon, lat, h)

# (name, lon, lat, h, proj_epsg or None for geographic)
CASES = [
    ("Earth2-equator-greenwich (geo 4979)",   0.0,   0.0,    0.0,   None),
    ("Earth2-midlat (geo 4979)",             10.21, 53.49,  38.0,   None),
    ("Earth2-southpole-ish (geo 4979)",      30.0, -80.0,  100.0,   None),
    ("Earth2-dateline (geo 4979)",          179.5,  12.3,   10.0,   None),
    ("NOAA NYC benchmark (UTM 18N)",        -73.985656, 40.748817, 0.0, 32618),
    ("Sydney (UTM 56S)",                    151.214,  -33.857,  58.0, 32756),
    ("Wellington (NZTM2000)",               174.7762, -41.2865, 5.0,  2193),
    ("Quito (UTM 17S equatorial)",          -78.4678, -0.1807, 2850.0, 32717),
    ("Svalbard (UTM 33N high-lat)",          15.65,    78.22,  10.0,  32633),
]

def main():
    geo4979 = None
    for name, lon, lat, h, epsg in CASES:
        if epsg is None:
            src = wkt(4979)
            x, y, z = lon, lat, h
        else:
            src = wkt(epsg)
            x, y, z = proj_en(lon, lat, h, epsg)
        gt = cf_ecef(lon, lat, h)
        # WKT has no tabs; ship it as a single field.
        print("\t".join([name, src, repr(x), repr(y), repr(z),
                          repr(float(gt[0])), repr(float(gt[1])), repr(float(gt[2]))]))

if __name__ == "__main__":
    main()
