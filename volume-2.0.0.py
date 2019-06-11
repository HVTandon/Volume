import rasterio as rio
import numpy as np
import json
from shapely.geometry import Polygon,Point
from math import *
from numba import jit
import utm
import time
import multiprocessing
import threading

def get_values(maxeast, mineast, maxnorth, minnorth):
    #converting latitude,longitude to utm 
    row_top, column_left  = src.index(mineast,maxnorth)
    row_bottom, column_right  = src.index(maxeast,minnorth)
    
    #indexing utm coordinates on raster file
    rows=row_bottom-row_top+1
    columns=column_right-column_left+1
    values = src.read( 1, window=rio.windows.Window(column_left, row_top, columns, rows))
    #storing elevation of coordinates in value array

    return values, rows, columns, row_top, column_left


'''Checking if the point lies inside the polygon''' 

def ray_tracing(row_start,row_end,column_start,column_end,itr_lat,itr_lon,poly,values,reference,res_cut,res_fill,it):
    #@jit(nopython=True)
    cut_thread=0
    fill_thread=0
    for x in range(row_start,row_end,itr_lat):
        for y in range(column_start,column_end,itr_lon):    

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

            if inside==True:
                val=values[x][y]
                if val==-10000:
                    val=reference
                elif val>reference:
                    cut_thread+=val-reference
                else :
                    fill_thread+=reference-val
    #print(cut_thread,fill_thread)
    res_cut[it]=cut_thread
    res_fill[it]=fill_thread
    #print(res_cut)
    #print(res_fill)




def mul_thre(row_start,row_end,column_start,column_end,itr_lat,itr_lon,poly,values,cut,fill,reference):
    
    res_cut=np.zeros(4)
    res_fill=np.zeros(4)
    
    
        
    t1=threading.Thread(target=ray_tracing, args=(row_start,int(row_end/2),column_start,int(column_end/2),itr_lat,itr_lon,poly,values,reference,res_cut,res_fill,0))
    t2=threading.Thread(target=ray_tracing, args=(int(row_end/2),row_end,column_start,int(column_end/2),itr_lat,itr_lon,poly,values,reference,res_cut,res_fill,1))
    t3=threading.Thread(target=ray_tracing, args=(row_start,int(row_end/2),int(column_end/2),column_end,itr_lat,itr_lon,poly,values,reference,res_cut,res_fill,2))
    t4=threading.Thread(target=ray_tracing, args=(int(row_end/2),row_end,int(column_end/2),column_end,itr_lat,itr_lon,poly,values,reference,res_cut,res_fill,3))
    
    #print(cut1, cut2, cut3, cut4)
    #print(fill1, fill2 , fill3 ,fill4)
    #print(cut_thread, fill_thread)

    t1.start()
    t2.start()
    t3.start()
    t4.start()

    t1.join()
    t2.join()
    t3.join()
    t4.join()
    
    #print(cut_thread, fill_thread)
    #cut=cut1+cut2+cut3+cut4
    #fill=fill1+fill2+fill3+fill4  
    cut.value=res_cut[0]+res_cut[1]+res_cut[2]+res_cut[3]
    fill.value=res_fill[0]+res_fill[1]+res_fill[2]+res_fill[3]
    #print(res_cut,res_fill,"-----------",cut.value,fill.value)




with open('Cadastre.geojson', 'r') as f:
    data=json.load(f)

easting=[]
northing=[]
point=[]
start = time.time()

for ty in data['features'][0]['geometry']['coordinates'][0]:
    east, north, zone_no, zone_letter=utm.from_latlon(ty[1], ty[0])
    #storing data in utm coordinate system
    easting.append(east)
    northing.append(north)

maxeast,mineast=max(easting),min(easting)
maxnorth,minnorth=max(northing),min(northing)

with rio.open('Cadastre_dsm.tif') as src: 
    
    '''Fetching resolution of tif file'''
    gt = src.transform

    pixelSizeX = gt[0]
    pixelSizeY =-gt[4]
    #pixelSizeX and pixelSizeY give pixel resolution

    values, rows, columns, row_top, column_left=get_values(maxeast, mineast, maxnorth, minnorth)
    

n=len(easting)
for i in range(n):
    row,col=src.index(easting[i],northing[i])
    point.append((row-row_top, col-column_left))

print(rows,columns)

#print("Please enter type of reference")
#ref=input()
ref='average'

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

itr_lat=1
#step size latitude wise : itr_lat
itr_lon=1
#step size longitude wise : itr_lon

sh_polygon=np.array(point)
cut=0.0
fill=0.0

cut1=multiprocessing.Value('f',0.0)
fill1=multiprocessing.Value('f',0.0)

cut2=multiprocessing.Value('f',0.0)
fill2=multiprocessing.Value('f',0.0)

cut3=multiprocessing.Value('f',0.0)
fill3=multiprocessing.Value('f',0.0)

cut4=multiprocessing.Value('f',0.0)
fill4=multiprocessing.Value('f',0.0)

#t1=multiprocessing.Process(target=ray_tracing, args=(x,y,sh_polygon,values,cut1,fill1,reference))
#t2=multiprocessing.Process(target=ray_tracing, args=(x,columns-1-y,sh_polygon,values,cut2,fill2,reference))
#t3=multiprocessing.Process(target=ray_tracing, args=(rows-1-x,y,sh_polygon,values,cut3,fill3,reference))
#t4=multiprocessing.Process(target=ray_tracing, args=(rows-1-x,columns-1-y,sh_polygon,values,cut4,fill4,reference))
#
#
#for x in range(0, int(rows/2), itr_lat):
#    for y in range(0, int(columns/2), itr_lon):
        
p1=multiprocessing.Process(target=mul_thre, args=(0,int(rows/2),0,int(columns/2),itr_lat,itr_lon,sh_polygon,values,cut1,fill1,reference))
p2=multiprocessing.Process(target=mul_thre, args=(int(rows/2),rows,int(columns/2),columns,itr_lat,itr_lon,sh_polygon,values,cut2,fill2,reference))
p3=multiprocessing.Process(target=mul_thre, args=(0,int(rows/2),int(columns/2),columns,itr_lat,itr_lon,sh_polygon,values,cut3,fill3,reference))
p4=multiprocessing.Process(target=mul_thre, args=(int(rows/2),rows,0,int(columns/2),itr_lat,itr_lon,sh_polygon,values,cut4,fill4,reference))
        
        #print(tt2-tt)

        # checks if point is inside the polygon
p1.start()
p2.start()
p3.start()
p4.start()

p1.join()
p2.join()
p3.join()
p4.join()

cut=cut1.value+cut2.value+cut3.value+cut4.value
fill=fill1.value+fill2.value+fill3.value+fill4.value
                       
fill_err=fill*1.5*(pixelSizeX*pixelSizeY)**1.5
# fill Error = elevation*1.5*(resolution i.e. pixel_width*pixel_length)**1.5
 
fill=-fill*itr_lon*itr_lat*pixelSizeX*pixelSizeY
cut_err=cut*1.5*(pixelSizeX*pixelSizeY)**1.5
# cut Error = elevation*1.5*(resolution i.e. pixel_width*pixel_length)**1.5

cut=cut*itr_lon*itr_lat*pixelSizeX*pixelSizeY
print(reference)
print(fill,"---------",cut,"-------",fill_err,"-------",cut_err)
end=time.time()
print(end-start)