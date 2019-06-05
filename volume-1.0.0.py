import rasterio as rio
from rasterio.windows import Window
import numpy as np
import matplotlib.pyplot as plt
import json
from shapely.geometry import Polygon, mapping
from math import *
from geographiclib.geodesic import Geodesic
from numba import jit
geod = Geodesic.WGS84  # define the WGS84 ellipsoid

geod.a, 1/geod.f
#geod.a gives equitorial radius and geod.f gives flattening of ellipsoid (f=0 means sphere)
pix_length=0.05
pix_width=0.05

@jit(nopython=True)
def ray_tracing(x,y,poly):
    n = len(poly)
    inside = False
    p2x = 0.0
    p2y = 0.0
    xints = 0.0
    p1x,p1y = poly[0]
    for i in range(n+1):
        p2x,p2y = poly[i % n]
        if y > min(p1y,p2y):
            if y <= max(p1y,p2y):
                if x <= max(p1x,p2x):
                    if p1y != p2y:
                        xints = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                    if p1x == p2x or x <= xints:
                        inside = not inside
        p1x,p1y = p2x,p2y

    return inside


with open('example_quarry2.geojson', 'r') as f:
    data=json.load(f)

lon=[]
lat=[]
point=[]

for ty in data['features'][0]['geometry']['coordinates'][0]:
    lon.append(ty[0])
    lat.append(ty[1])
    point.append((ty[0],ty[1]))
print(point)
#print(lat)

sh_polygon = Polygon(point)
#print(sh_polygon)

maxlat,minlat=max(lat),min(lat)
maxlon,minlon=max(lon),min(lon)
print(maxlat,minlat,maxlon,minlon)

''' Calculating step size for iterating longitude'''
l = geod.InverseLine(maxlat, 0, maxlat+1, 0)
# l is a geodesic line.
#l.s13 gives the distance between the 2 input coordinates i.e. coordinates in lon_lat
#step_size is in metres
step_size = pix_length
#l.Position gives the coordinates of the point on the line at a distance 's'.
g = l.Position(step_size, Geodesic.STANDARD | Geodesic.LONG_UNROLL)
print(g['lat2'])
itr_lon=g['lat2']-maxlat

''' Calculating step size for iterating longitude'''
l = geod.InverseLine(0, maxlon, 0, maxlon+1)
# l is a geodesic line.
#l.s13 gives the distance between the 2 input coordinates i.e. coordinates in lon_lat
#step_size is in metres
step_size = pix_width
#l.Position gives the coordinates of the point on the line at a distance 's'.
g = l.Position(step_size, Geodesic.STANDARD | Geodesic.LONG_UNROLL)
itr_lat=g['lon2']-maxlon


sh_polygon=np.array(point)
print(sh_polygon.dtype)
print(itr_lat,"    ",itr_lon)

i=0
j=0
for x in np.arange(minlon, maxlon, itr_lon):
    for y in np.arange(minlat, maxlat, itr_lat):
        inside1 = [ray_tracing(x, y, sh_polygon)]
        if inside1==[True]:
            j+=1
        print(x, y, inside1)
        i+=1
print(i,"-----------------------",j)