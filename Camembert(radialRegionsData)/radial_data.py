from qgis.core import (QgsVectorLayer, QgsField, QgsSpatialIndex, QgsFeature,
                       QgsGeometry, QgsPointXY, QgsVectorDataProvider)
from PyQt5.QtCore import QVariant
import math
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt


def count_overlapping_shapes(first_shapefile_path, second_shapefile_path):
    # Load the shapefiles as QGIS vector layers
    first_layer = QgsVectorLayer(first_shapefile_path, 'First Layer', 'ogr')
    second_layer = QgsVectorLayer(second_shapefile_path, 'Second Layer', 'ogr')

    if not first_layer.isValid() or not second_layer.isValid():
        print("Error: Invalid layer(s)!")
        return

    # Create a spatial index for the second layer
    second_spatial_index = QgsSpatialIndex(second_layer)
    a_values = []
    b_values = []
    a_values_FD = []
    b_values_FD = []
    areas = []
    graph_color = ['black']
    
    for first_feature in first_layer.getFeatures():
        geom = first_feature.geometry()
        areas.append(int(geom.area()))
    areas = [*set(areas)]
    areas_new = []
    for area in areas:
        if area < 1000000:
            areas_new.append(area)
    areas_new.sort()
    colors = {areas_new[0]: "red"}

    # Iterate through each feature in the first layer
    for first_feature in first_layer.getFeatures():
        
        geom = first_feature.geometry()
        space = int(geom.area())    
        if not space > 1000000:
            graph_color.append(colors[space])
            
            # lets initialize a array of boulder diams for each sector
            diameters = []
            
            # Get the geometry of the first feature
            first_geometry = first_feature.geometry()

            # Find the intersecting features in the second layer using the spatial index
            intersecting_feature_ids = second_spatial_index.intersects(first_geometry.boundingBox())

            # Count the number of overlapping shapes
            num_overlapping_shapes = 0
            for intersecting_id in intersecting_feature_ids:
                intersecting_feature = second_layer.getFeature(intersecting_id)
                intersecting_geometry = intersecting_feature.geometry()
                
                # We've found an overlapping boulder!
                if first_geometry.intersects(intersecting_geometry):
                    # for the cumul density, lets iterate num_overlapping_shapes
                    num_overlapping_shapes += 1
                    
                    # Now for the csfds, lets get the boulders diameter
                    area = intersecting_geometry.area()
                    diameters.append(2 * (math.sqrt(area / math.pi)))
            ################################
            # Compute the b-value of the power-law
            def power_law(x, a, b):
                return a * np.power(x, b)
                
            # Fill bins and frequency distribs
            bin_counts = []
            diameter_bins = []
            
            # The diameters of all boulders in this region
            diams = np.array(diameters)
            
            # Create log bins
            data_min = np.min(diams)
            data_max = np.max(diams)
            num_bins = 100
            log_bins = np.logspace(np.log10(data_min), np.log10(data_max), num_bins)

            
            # nums for FD
            freq, _ = np.histogram(diams, bins=log_bins)
            
            # lets get rid of all those zeros, create a power-log reg, then add it to a figure
            counts = []
            fd_bins = []
            for i in range(len(freq)):
                count = freq[i]
                bin = log_bins[i]
                if count != 10000:
                    counts.append(count)
                    fd_bins.append(bin)
            params, covariance = curve_fit(power_law, fd_bins, counts)
            aFD, bFD = params
            bFD = float(bFD)
            aFD = float(aFD)
            a_values_FD.append(aFD)
            b_values_FD.append(bFD)
            
            
            # get nums for CFD
            for bin in log_bins:
        
                count = 0
                # Count each boulder in the current bin, If there are none in thed bin, next bin
                for diameter in diameters:
                    if diameter > bin:
                        count+=1
                if count == 0:
                    continue
                else:
                    # If the bin contains boulders, append to the yvals
                    diameter_bins.append(bin)
                    bin_counts.append(count)
                    
            # Perform the power law regression if the bins are not empty
            if len(diameter_bins) > 1 and len(bin_counts) > 1:
                params, covariance = curve_fit(power_law, diameter_bins, bin_counts)
                a, b = params
                b = float(b)
                a = float(a)
            else:
                b = 0.0000
                a = 0.0000
            ################################
            a_values.append(a)
            b_values.append(b)
            density = (num_overlapping_shapes / first_geometry.area()) * 100000
            attrs = {first_layer.fields().lookupField('density'): density, first_layer.fields().lookupField('bval'): b, first_layer.fields().lookupField('aval'): a, first_layer.fields().lookupField('bval_FD'): bFD, first_layer.fields().lookupField('aval_FD'): aFD}
            first_layer.dataProvider().changeAttributeValues({first_feature.id(): attrs})
            # first_layer.dataProvider().changeAttributeValue({first_feature.id(): {first_layer.fields().lookupField('b-value'): b}})

    # Plot the data
    regions = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16']
    for a, b, aFD, bFD, color, region in zip(a_values, b_values, a_values_FD, b_values_FD, graph_color, regions):
        plt.figure()
        y = power_law(diameter_bins, a, b)
        label = f"CSFD power-law, b-val = {b}"
        plt.plot(diameter_bins, y, color = "red", label = label)
        
        y2 = power_law(log_bins, aFD, bFD)
        label2 = f"FD power-law, b-val = {bFD}"
        plt.plot(log_bins, y2, color = "blue", label = label2)
        plt.xlabel('Boulder Diameter')
        plt.ylabel('Number of Boulders <= Diameter')
        plt.title("cp1701 CSFDs by radial/concentric sectors")
        plt.legend()
        plt.loglog()
        plt.savefig("/Users/coltenrodriguez/Desktop/Stanford_EPSP_23/cp0394_figures/" + region)
        plt.show()    
    
# Camembert shapefile
first_shapefile_path = "/Users/coltenrodriguez/Desktop/Stanford_EPSP_23/cp0394_camemberts.shp"
# Shapefile containing boulder outlines
second_shapefile_path = "/Users/coltenrodriguez/Desktop/Stanford_EPSP_23/crater0394/shp/inputs/M1221383405-crater0394-boulder-mapping.shp"

# create the density field
layer = QgsVectorLayer(first_shapefile_path)
layer_provider=layer.dataProvider()
layer_provider.addAttributes([QgsField("density",QVariant.Int), QgsField("bval",QVariant.Double), QgsField("aval",QVariant.Double), QgsField("bval_FD",QVariant.Double), QgsField("aval_FD",QVariant.Double)])
layer.updateFields()

count_overlapping_shapes(first_shapefile_path, second_shapefile_path)

