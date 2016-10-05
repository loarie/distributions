# Directory setup
Make a directory called raster_data and fill it with the 17 rasters you can find here XXX
also make a directory called out_data for the output data.

# Dependencies
fit_model.r runs in R and takes a output.csv as an input, runs a model, an produces coefficients (coefs) used by the python scripts
process_shapes_p1.py runs in Python and takes a taxon_id and a list of atlas listings as in puts and along with rasters in raster_data produces the table (output.csv) needed to run the model
process_shapes_p2.py runs in Python and runs fit_model.r and then produces rasters of predictions (predict.tif) and thresholded predictions (predict_thres.tif)

#Aditional steps
I was exploring coarsening the thresholded predictions 
```gdalwarp -tr 0.05 0.05 -r average out_data/predict_thres.tif out_data/predict_warp.tif```

converting them into shapefile form
```
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

wd = '/Users/scottloarie/niche_models/'
sourceRaster = gdal.Open(wd+'out_data/predict_warp.tif')
band = sourceRaster.GetRasterBand(1)
bandArray = band.ReadAsArray()
outShapefile = "out_data/predict"
driver = ogr.GetDriverByName("ESRI Shapefile")
if os.path.exists(outShapefile+".shp"):
 driver.DeleteDataSource(outShapefile+".shp")

outDatasource = driver.CreateDataSource(outShapefile+ ".shp")
outLayer = outDatasource.CreateLayer("predict", srs=None)
gdal.Polygonize( band, band, outLayer, -1, [], callback=None )
outDatasource.Destroy()
sourceRaster = None
```

add adding a 0.1 degree dissolved buffer in qgis
