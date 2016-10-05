from __future__ import division
import time
import urllib, json
import random
from osgeo import ogr
import math
from osgeo import gdal
import numpy as np
import os, sys
import csv
import rpy2.robjects
from osgeo.gdalconst import *

#
# take taxon_id and listings to make a table of env covariates in order to fit the model
#

startTime = time.time()

#inputs are a taxon_id (using the public API to get observations at the moment)...
taxon_id = 60983
#...and the set of atlas presence places (place_ids) which is hardcoded here
place_ids = [2764, 854, 1919, 2319, 1250, 1527, 1921, 418]

wd = '/Users/scottloarie/niche_models/'

#get presence data using the public api
print "getting the presence data..."
presences = []
url = "http://api.inaturalist.org/v1/observations?verifiable=true&taxon_id="+str(taxon_id)
response = urllib.urlopen(url)
data = json.loads(response.read())
pages = int(math.ceil(data["total_results"] / data["per_page"]))
for row in data["results"]:
 coords = row["geojson"]["coordinates"]
 presences.append([float(coords[0]), float(coords[1])])

for page in range(1,pages):
 url = "http://api.inaturalist.org/v1/observations?verifiable=true&taxon_id="+str(taxon_id)+"&page="+str(page+1)
 response = urllib.urlopen(url)
 data = json.loads(response.read())
 for row in data["results"]:
  if row["geojson"]:
   coords = row["geojson"]["coordinates"]
   presences.append([float(coords[0]), float(coords[1])])

#loop through the atlas presence places to calculate their area, make a shapefile for later use, and store them to sample from shortly...
print "looping through the atlas presence places to get areas and make a shapefile..."
outputMergefn = wd+'out_data/atlas_mask.shp'
driverName = 'ESRI Shapefile'
out_driver = ogr.GetDriverByName( driverName )
if os.path.exists(outputMergefn): #delete the shapefile if it exists
 out_driver.DeleteDataSource(outputMergefn)

out_ds = out_driver.CreateDataSource(outputMergefn)
geometryType = ogr.wkbPolygon
out_layer = out_ds.CreateLayer(outputMergefn, geom_type=geometryType)

areas = 0
polygons = []
for place_id in place_ids:
 #fetch the geom
 url = "http://www.inaturalist.org/places/geometry/"+str(place_id)+".geojson"
 response = urllib.urlopen(url)
 data = json.loads(response.read())
 geom = json.dumps(data)
 polygon = ogr.CreateGeometryFromJson(geom)
 #store it for later
 polygons.append(polygon)
 #accumulate the total area
 area = polygon.GetArea()
 areas += area
 #append to a shapefile
 out_feat = ogr.Feature(out_layer.GetLayerDefn())
 out_feat.SetGeometry(polygon)
 out_layer.CreateFeature(out_feat)
 out_layer.SyncToDisk()

#rasterize the atlas mask
rasterfile = wd+'raster_data/z01.tif'
aoi_raster = gdal.Open(rasterfile)

def new_raster_from_base(base, outputURI, format, nodata, datatype):
 cols = base.RasterXSize
 rows = base.RasterYSize
 projection = base.GetProjection()
 geotransform = base.GetGeoTransform()
 bands = base.RasterCount
 driver = gdal.GetDriverByName(format)
 new_raster = driver.Create(str(outputURI), cols, rows, bands, datatype)
 new_raster.SetProjection(projection)
 new_raster.SetGeoTransform(geotransform)
 for i in range(bands):
  new_raster.GetRasterBand(i + 1).SetNoDataValue(nodata)
  new_raster.GetRasterBand(i + 1).Fill(nodata)
 
 return new_raster

shape_uri = wd+'out_data/atlas_mask.shp'
shape_datasource = ogr.Open(shape_uri)
shape_layer = shape_datasource.GetLayer()
raster_out = wd+'out_data/atlas_mask.tif'
raster_dataset = new_raster_from_base(aoi_raster, raster_out, 'GTiff' ,-1, gdal.GDT_Int32)
band = raster_dataset.GetRasterBand(1)
nodata = band.GetNoDataValue()
band.Fill(nodata)
gdal.RasterizeLayer(raster_dataset, [1], shape_layer, burn_values=[1])


#generate random background points
n=10000 #number of background points we want randomly and evenly distributed across all the atlas presence places
print "generating random background points..."
background_points = []
for polygon in polygons: #loop through each atlas presence place
 env = polygon.GetEnvelope()
 xmin, ymin, xmax, ymax = env[0],env[2],env[1],env[3]
 area = polygon.GetArea()
 num_points = int(math.ceil(n * area / areas)) #scale the number of random points to generate for this atlas presence place by its area
 counter = 0
 while counter < num_points: #generate random points within the bounding box untill you have enough within the place to keep
  point = ogr.Geometry(ogr.wkbPoint)
  point.AddPoint(random.uniform(xmin, xmax), random.uniform(ymin, ymax))
  if point.Within(polygon):
   pos_x = point.GetX()
   pos_y = point.GetY()
   background_points.append([pos_x,pos_y])
   counter += 1

#loop through the rasters to sample the environmental data at the presence and background points  #conv3.py
print "looping through the rasters to sample the environmental data at the presence and background points.."
#rasters = ["mean_temp","sd_temp","mean_prec","sd_prec","consensus_full_class_1_ext","consensus_full_class_2_ext","consensus_full_class_3_ext","consensus_full_class_4_ext","consensus_full_class_5_ext","consensus_full_class_6_ext","consensus_full_class_7_ext","consensus_full_class_8_ext","consensus_full_class_9_ext","consensus_full_class_10_ext","consensus_full_class_11_ext","consensus_full_class_12_ext","new_raster_big3"]
rasters = ["mean_temp","sd_temp","mean_prec","sd_prec","c01","c02","c03","c04","c05","c06","c07","c08","c09","c10","c11","c12","z01"]
background_samples = []
presence_samples = []
for raster in rasters:
 print "working on "+raster
 rasterfile = wd+'raster_data/'+raster+'.tif'
 gdata = gdal.Open(rasterfile)
 gt = gdata.GetGeoTransform()
 data = gdata.ReadAsArray().astype(np.float)
 gdata = None
 background_sample = []
 presence_sample = []
 #sample background data
 print "sampling background data..."
 for point in background_points:
  x = int((point[0] - gt[0])/gt[1])
  y = int((point[1] - gt[3])/gt[5])
  background_sample.append(data[y, x])
 
 #sample presence data
 print "sampling presence data..."
 for presence in presences:
  x = int((presence[0] - gt[0])/gt[1])
  y = int((presence[1] - gt[3])/gt[5])
  presence_sample.append(data[y, x])
 
 background_samples.append(background_sample)
 presence_samples.append(presence_sample)

#write a csv with the data
print "writing a csv with the data..."
with open(wd+'out_data/output.csv', 'wb') as csvfile:
 csvwriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
 csvwriter.writerow(['y','t1','t2','p1','p2','c1','c2','c3','c4','c5','c6','c7','c8','c9','c10','c11','c12','z1','lon','lat'])
 for i in range(len(background_points)):
  row = [0]
  for j in range(len(rasters)):
   row.append(background_samples[j][i])
  
  row.append(background_points[i][0])
  row.append(background_points[i][1])
  csvwriter.writerow(row)
 
 for i in range(len(presences)):
  row = [1]
  for j in range(len(rasters)):
   row.append(presence_samples[j][i])
	
  row.append(presences[i][0])
  row.append(presences[i][1])
  csvwriter.writerow(row)

print "elapsed time in seconds:"
print time.time() - startTime