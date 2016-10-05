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
# take the table of data to fit the model and make predictions
#

startTime = time.time()

wd = '/Users/scottloarie/niche_models/'

#run the actual regression in R using the above csv data
print "running the actual regression in R..."
f = file("fit_model.R")
code = ''.join(f.readlines())
result = rpy2.robjects.r(code)
coefs = rpy2.robjects.globalenv['coefs']

#use the model to make predictions across the grid
print "using the model to make predictions across the grid..."
rasters = ["c01","c02","c03","c04","c05","c06","c07","c08","c09","c10","c11","c12"]
rasterfile = wd+'raster_data/'+rasters[0]+'.tif'
gdata = gdal.Open(rasterfile)
gt = gdata.GetGeoTransform()
data = gdata.ReadAsArray().astype(np.float)
gdata = None
calc = coefs[0] + coefs[9] * data
for i in range(1,len(rasters)):
 print rasters[i]
 rasterfile = wd+'raster_data/'+rasters[i]+'.tif'
 gdata = gdal.Open(rasterfile)
 gt = gdata.GetGeoTransform()
 data = gdata.ReadAsArray().astype(np.float)
 gdata = None
 calc += coefs[i+9] * data

rasters = ["mean_temp","sd_temp","mean_prec","sd_prec"]
for i in range(len(rasters)):
 print rasters[i]
 rasterfile = wd+'raster_data/'+rasters[i]+'.tif'
 gdata = gdal.Open(rasterfile)
 gt = gdata.GetGeoTransform()
 data = gdata.ReadAsArray().astype(np.float)
 data[data == -9999.0] = np.NaN
 gdata = None
 calc += coefs[i+1] * data + coefs[i+5] * data * data

rasterfile = wd+'out_data/atlas_mask.tif'
gdata = gdal.Open(rasterfile)
gt = gdata.GetGeoTransform()
nodata = gdata.ReadAsArray().astype(np.float)
print nodata[0,0]
calc[nodata != 1.0] = np.NaN
calc = np.exp(calc)
gdata = None

calc[np.isnan(calc)]= -9999.0

#save the prediction
raster = rasters[0]
rasterfile = wd+'raster_data/'+raster+'.tif'
gdata = gdal.Open(rasterfile)
gt = gdata.GetGeoTransform()

gdal.AllRegister()
rows = gdata.RasterYSize
cols = gdata.RasterXSize
driver = gdata.GetDriver()
outDs = driver.Create(wd+'out_data/predict.tif', cols, rows, 1, GDT_Float32)
outBand = outDs.GetRasterBand(1)
outBand.WriteArray(calc, 0, 0)
outBand.FlushCache()
outBand.SetNoDataValue(-9999)
outDs.SetGeoTransform(gdata.GetGeoTransform())
outDs.SetProjection(gdata.GetProjection())

#rasterfile = '/Users/scottloarie/niche_models/global_grids/predict.tif'
#gdata = gdal.Open(rasterfile)
#calc = gdata.ReadAsArray().astype(np.float)
calc[calc == -9999.0] = np.NaN

presences = []
with open(wd+'out_data/output.csv', 'rb') as csvfile:
 csvreader = csv.reader(csvfile, delimiter=',', quotechar='|')
 next(csvreader)
 for row in csvreader:
  if int(row[0]) == 1:
   presences.append([float(row[18]),float(row[19])])

##threshold - using quantile of traning data
presence_sample = []
for presence in presences:
 x = int((presence[0] - gt[0])/gt[1])
 y = int((presence[1] - gt[3])/gt[5])
 presence_sample.append(calc[y, x])

presence_sample.sort()
cutoff = int(round(len(presences)*0.05))
minthres = presence_sample[cutoff] #np.nanmin(presence_sample)
print minthres
calc[calc < minthres] = 0
calc[calc >= minthres] = 1
calc[np.isnan(calc)]= -9999.0

gdal.AllRegister()
rows = gdata.RasterYSize
cols = gdata.RasterXSize
driver = gdata.GetDriver()
outDs = driver.Create(wd+'out_data/predict_thres.tif', cols, rows, 1, GDT_Int32)
outBand = outDs.GetRasterBand(1)
outBand.WriteArray(calc, 0, 0)
outBand.FlushCache()
outBand.SetNoDataValue(-9999)
outDs.SetGeoTransform(gdata.GetGeoTransform())
outDs.SetProjection(gdata.GetProjection())
gdata = None

print "elapsed time in seconds:"
print time.time() - startTime