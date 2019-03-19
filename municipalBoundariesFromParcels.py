import sys
import os
import datetime
from osgeo import ogr


startDT = datetime.datetime.now()
print ('Start Time for Script: %s' % str(startDT))

daShapefile = sys.argv[1] 

driver = ogr.GetDriverByName('ESRI Shapefile')

dataSource = driver.Open(daShapefile, 0) 

# Check to see if shapefile is found.
if dataSource is None:
    print ('Could not open %s' % (daShapefile))
else:
    print ('Opened %s' % (daShapefile))

    #Get Union of Geometries for Each Town  
    layer = dataSource.GetLayer()
    print ("Unioning features")
    sql='''SELECT ST_Union(geometry) AS geometry, TOWN AS TOWN_NAME FROM {layername} GROUP BY TOWN_NAME'''.format(layername=layer.GetName())
    dialect='''SQLITE'''
    unionedLayer = dataSource.ExecuteSQL(sql,None,dialect)

    #output file
    #include datetimestamp in filename
    outputFileName = '''output-{datetimestamp}.shp'''.format(datetimestamp=str(datetime.datetime.now()))
    outDriver = ogr.GetDriverByName('ESRI Shapefile')
    outputDS = outDriver.CreateDataSource(outputFileName)
    # copy the spatial reference & geometry from the unionedLayer
    srs = unionedLayer.GetSpatialRef()
    geometry = unionedLayer.GetGeomType()
    
    # create the layer
    outputLayer = outputDS.CreateLayer("output",srs, geometry)    

    # Add the fields we're interested in
    outputLayer.CreateField(ogr.FieldDefn("ID", ogr.OFTInteger))
    town_name = ogr.FieldDefn("TOWN_NAME", ogr.OFTString)
    outputLayer.CreateField(town_name)
    geometryField = ogr.FieldDefn("GEOMETRY",ogr.OFTString)
    outputLayer.CreateField(geometryField)

    ID=1
    
    print("Removing Holes & Slivers") 
    for feature in unionedLayer:
        outputFeature =  ogr.Feature(outputLayer.GetLayerDefn())
        outputFeature.SetField("ID", ID)
        #print(ID)
        ID += 1
        
        outputFeature.SetField("TOWN_NAME", feature.GetFieldAsString("TOWN_NAME"))
        
        #Since we are interested in geometries without holes or slivers, we just want the external ring of the polygon
        geomRef = feature.GetGeometryRef()
        geom = geomRef.Clone()
        externalRingRef = geom.GetGeometryRef(0)       

        #This test needed to be done, because two cases- Sunderland & Windham were composed of two non-intersecting polygons that are very close
        #Can demonstrate in QGIS
        geometryType=externalRingRef.Clone().GetGeometryType()
        
        #This is a linear ring, we're good. Otherwise, we have to go down one more level
        if geometryType == 2: 
           poly = ogr.Geometry(ogr.wkbPolygon)
           poly.AddGeometry(externalRingRef.Clone())
        else:
           geom=externalRingRef.Clone()
           externalRingRef2=geom.GetGeometryRef(0)
           poly = ogr.Geometry(ogr.wkbPolygon)
           poly.AddGeometry(externalRingRef2.Clone())

        #Convert polygon to a string to output to GEOMETRY field
        polyStr = str(poly)

        outputFeature.SetField("GEOMETRY", polyStr)
        outputFeature.SetGeometry(poly)
        outputLayer.CreateFeature(outputFeature)
        #write feature
        outputFeature = None
    unionedLayer.ResetReading()

    #write shapefile
    outputDS = None
    
    endDT = datetime.datetime.now()
    print('End Time for Script: %s' % str(endDT))
    duration=str((endDT-startDT).seconds)
    print('Duration for Script in Seconds: %s' % duration)
