import rasterio as rio
import numpy as np
import json
from shapely.geometry import Polygon,Point
from math import *
from geographiclib.geodesic import Geodesic
from numba import jit
import utm
import time
geod = Geodesic.WGS84  # define the WGS84 ellipsoid

geod.a, 1/geod.f
#geod.a gives equitorial radius and geod.f gives flattening of ellipsoid (f=0 means sphere)


def get_values(maxeast, mineast, maxnorth, minnorth):
    #print(lon, lat)
    #east_left, north_top, zone_no, zone_letter = utm.from_latlon(maxlat,minlon)
    #east_right, north_bottom, zone_no, zone_letter = utm.from_latlon(minlat,maxlon)
    #print(east, north, zone_no, zone_letter)
    #converting latitude,longitude to utm 
    row_top, column_left  = src.index(mineast,maxnorth)
    row_bottom, column_right  = src.index(maxeast,minnorth)
    #print(row,column)
    #indexing utm coordinates on raster file
    rows=row_bottom-row_top+1
    columns=column_right-column_left+1
    values = src.read( 1, window=rio.windows.Window(column_left, row_top, columns, rows))
    #print(values)
    #getting elevation value at that index
    #print(east_left,east_right,north_top,north_bottom)
    return values, rows, columns, row_top, column_left

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

with open('example_quarry2.geojson', 'r') as f:
    data=json.load(f)

easting=[]
northing=[]
point=[]
cut=0.0
fill=0.0
start = time.time()

for ty in data['features'][0]['geometry']['coordinates'][0]:
    #lon.append(ty[0])
    #lat.append(ty[1])
    east, north, zone_no, zone_letter=utm.from_latlon(ty[1], ty[0])
    #point.append((east, north))
    easting.append(east)
    northing.append(north)
#print(lat)
#print(lon)

maxeast,mineast=max(easting),min(easting)
maxnorth,minnorth=max(northing),min(northing)
#print(maxlat, minlat, maxlon+0.0001, minlon+0.0001)

with rio.open('example_quarry2_dsm.tif') as src: 
    num_bands = src.count
    gt = src.transform

    pixelSizeX = gt[0]
    pixelSizeY =-gt[4]
    #pixelSizeX and pixelSizeY give pixel resolution

    values, rows, columns, row_top, column_left=get_values(maxeast, mineast, maxnorth, minnorth)
    

n=len(easting)
for i in range(n):
    #east, north, zone_no, zone_letter=utm.from_latlon(lat[i], lon[i])
    row,col=src.index(easting[i],northing[i])
    point.append((row-row_top, col-column_left))
    #print(lat[i],lon[i],"------",east,north,"------",point[i])
    #print(point[i][0],point[i][1])
    #print(values[point[i][0]][point[i][1]])

#print(point)

print("Please enter type of reference")
ref=input()

ref_list=np.zeros(n)

for i in range(n):
    ref_list[i]=values[point[i][0]][point[i][1]]

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

sh_polygon = Polygon(point)
#print(sh_polygon)

#print(maxlat,minlat,maxlon,minlon)

itr_lat=4
itr_lon=4

sh_polygon=np.array(point)
#print(sh_polygon.dtype)
print(itr_lat,"    ",itr_lon)

i=0
j=0

for x in np.arange(0, rows, itr_lat):
    for y in np.arange(0, columns, itr_lon):
        i+=1
        p1=Point(x,y)
        #print(x,y)
        #inside1=p1.within(sh_polygon)
        inside1 = ray_tracing(x, y, sh_polygon)
        if inside1==True:
            j+=1
            val=values[x][y]
            if val==-10000:
                val=reference
            elif val>reference:
                cut+=val-reference
            else :
                fill+=reference-val
            #print(x, y, inside1)        

print(cut,fill)           
fill_err=fill*1.5*(pixelSizeX*pixelSizeY)**1.5
fill=-fill*itr_lon*itr_lat*pixelSizeX*pixelSizeY
cut_err=cut*1.5*(pixelSizeX*pixelSizeY)**1.5
cut=cut*itr_lon*itr_lat*pixelSizeX*pixelSizeY
print(reference)
print(np.amax(ref_list))
print(i,"--------------", j)
print(fill,"---------",cut,"-------",fill_err,"-------",cut_err)
end=time.time()
print(end-start)