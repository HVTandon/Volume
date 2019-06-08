import rasterio as rio
from rasterio.windows import Window
import numpy as np
import matplotlib.pyplot as plt
import json
from shapely.geometry import Polygon, mapping,Point
from math import *
from geographiclib.geodesic import Geodesic
from numba import jit
import utm
import time
geod = Geodesic.WGS84  # define the WGS84 ellipsoid

geod.a, 1/geod.f
#geod.a gives equitorial radius and geod.f gives flattening of ellipsoid (f=0 means sphere)
pix_length=0.125
pix_width=0.125


def get_values(lon, lat):
    #print(lon, lat)
    east, north, zone_no, zone_letter = utm.from_latlon(lat,lon)
    #print(east, north, zone_no, zone_letter)
    #converting latitude,longitude to utm 
    row, column  = src.index(east,north)
    #print(row,column)
    #indexing utm coordinates on raster file
    values = float(src.read( 1, window=rio.windows.Window(column, row, 1, 1)))
    #getting elevation value at that index
    return values

#@jit(nopython=True)
def ray_tracing(x,y,poly):
    n = len(poly)
    #print(n)
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

with open('Romont3D.geojson', 'r') as f:
    data=json.load(f)

lon=[]
lat=[]
point=[]
cut=0.0
fill=0.0

for ty in data['features'][0]['geometry']['coordinates'][0]:
    lon.append(ty[0])
    lat.append(ty[1])
    point.append((ty[0],ty[1]))
#print(lat)
#print(lon)

print("Please enter type of reference")
ref=input()

n=len(lon)
ref_list=np.zeros(n)
with rio.open('Romont3D_dsm.tif') as src:
    #print(src.count)
    for i in range(n):
        ref_list[i]=get_values(lon[i], lat[i])

if ref=='average':  
    reference=np.average(ref_list)
elif ref=='lowest':
    reference=np.amin(ref_list)
elif ref=='highest':
    reference=np.amax(ref_list)
elif ref=='custom':
    print("Give a custom value")
    reference=float(input())
else :
    print("WRONG INPUT")

start = time.time()

sh_polygon = Polygon(point)
#print(sh_polygon)

maxlat,minlat=max(lat),min(lat)
maxlon,minlon=max(lon),min(lon)
#print(maxlat,minlat,maxlon,minlon)

''' Calculating step size for iterating longitude'''
l = geod.InverseLine(minlat, (maxlon+minlon)/2, maxlat, (maxlon+minlon)/2)
# l is a geodesic line.
#l.s13 gives the distance between the 2 input coordinates i.e. coordinates in lon_lat
#step_size is in metres
step_size = pix_length
#l.Position gives the coordinates of the point on the line at a distance 's'.
g = l.Position(step_size, Geodesic.STANDARD | Geodesic.LONG_UNROLL)
#print(g['lat2'])
itr_lat=g['lat2']-minlat

''' Calculating step size for iterating longitude'''
l = geod.InverseLine((maxlat+minlat)/2, minlon, (maxlat+minlat)/2, maxlon)
# l is a geodesic line.
#l.s13 gives the distance between the 2 input coordinates i.e. coordinates in lon_lat
#step_size is in metres
step_size = pix_width
#l.Position gives the coordinates of the point on the line at a distance 's'.
g = l.Position(step_size, Geodesic.STANDARD | Geodesic.LONG_UNROLL)
itr_lon=g['lon2']-minlon


sh_polygon=np.array(point)
#print(sh_polygon.dtype)
#print(itr_lat,"    ",itr_lon)

i=0
j=0

with rio.open('Romont3D_dsm.tif') as src: 
    num_bands = src.count
    #print(src.count)
    for x in np.arange(minlon, maxlon, itr_lon):
        for y in np.arange(minlat, maxlat, itr_lat):
            i+=1
            p1=Point(x,y)
            #print(x,y)
            #inside1=p1.within(sh_polygon)
            inside1 = ray_tracing(x, y, sh_polygon)
            if inside1==True:
                j+=1
                val=get_values(x, y)
                if val==-10000:
                    val=reference
                if val>reference:
                    cut+=val-reference
                else :
                    fill+=reference-val
                #print(x, y, inside1)        
            
fill=fill*pix_length*pix_width
fill_err=fill*1.5*pix_length
cut=cut*pix_length*pix_width
cut_err=cut*1.5*pix_length
print(reference)
print(np.amax(ref_list))
print(i,"--------------", j)
print(fill,"-----------------------",cut,"---------",fill_err,"-----------",cut_err)
end=time.time()
print(end-start)