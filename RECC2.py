import META
import cv2
import numpy as np
import numpy.matlib
import matplotlib.pyplot as plt
import os
from random import randint
from math import cos, sin, asin, sqrt, radians, log, tan, exp, atan2, atan
from random import randint
import warnings
warnings.simplefilter(action = "ignore", category = RuntimeWarning)

                
def patch_match(pixel_size, w, s, dst_max, edges1C, gt, fact_x, fact_y, x_b, y_b, edges0C, gt_0, fact_x_0, fact_y_0, x_b_0, y_b_0, mask_o_0):
    max_dist = int((dst_max)/pixel_size)
    bound1 = mask_o_0.shape[0]
    bound2 = mask_o_0.shape[1]
    grid = []
    for i in range(max_dist+w,bound1-max_dist-w,s):
        for j in range(max_dist+w,bound2-max_dist-w,s):
            if mask_o_0[i,j] == 0:
                grid.append((i,j))
    target_l   = []
    patch_l    = []
    RECC_l     = []
    cv         = np.zeros(len(grid)) 
    dist       = np.zeros(len(grid))
    dist_lon   = np.zeros(len(grid))
    dist_lat   = np.zeros(len(grid))
    origin_x   = np.zeros(len(grid))
    origin_y   = np.zeros(len(grid))
    target_lon = np.zeros(len(grid))
    target_lat = np.zeros(len(grid))
    o_x        = np.zeros(len(grid))
    o_y        = np.zeros(len(grid))
    t_x        = np.zeros(len(grid))
    t_y        = np.zeros(len(grid))
    RECC_s = np.zeros(edges1C.shape)
    for i in range(len(grid)):
        print(i,len(grid))
        x_i_0 = grid[i][0]
        y_i_0 = grid[i][1]
        target = edges0C[x_i_0-w:x_i_0+w,y_i_0-w:y_i_0+w]
        sum_target = np.sum(target)
        search_area = edges1C[x_i_0-max_dist-w:x_i_0+max_dist+w,y_i_0-max_dist-w:y_i_0+max_dist+w]
        sum_patch = cv2.filter2D(search_area,-1,np.ones(target.shape))
        numerator = cv2.filter2D(search_area,-1,target)
        RECC = numerator / (sum_patch+sum_target)
        RECC_s.fill(np.NaN)
        RECC_s[x_i_0-max_dist:x_i_0+max_dist,y_i_0-max_dist:y_i_0+max_dist] = RECC[w:-w,w:-w]
        RECC_l.append(RECC_s)
        max_one  = np.partition(RECC_s[~np.isnan(RECC_s)].flatten(),-1)[-1]
        max_n    = np.partition(RECC_s[~np.isnan(RECC_s)].flatten(),-4-1)[-4-1]
        y_i      = np.where(RECC_s >= max_one)[1][0]  
        x_i      = np.where(RECC_s >= max_one)[0][0]
        y_n      = np.where(RECC_s >= max_n)[1][0:-1]
        x_n      = np.where(RECC_s >= max_n)[0][0:-1]
        cv[i] = sum(np.sqrt(np.square(x_i-x_n)+np.square(y_i-y_n)))
        lon = gt[0] + gt[1]*y_i*fact_x + gt[2]*x_i*fact_y
        lat = gt[3] + gt[4]*y_i*fact_x + gt[5]*x_i*fact_y
        lon_0 = gt_0[0] + gt_0[1]*y_i_0*fact_x_0 + gt_0[2]*x_i_0*fact_y_0
        lat_0 = gt_0[3] + gt_0[4]*y_i_0*fact_x_0 + gt_0[5]*x_i_0*fact_y_0
        dist[i] = META.calc_distance(lat,lon,lat_0,lon_0)
        dist_lon[i] = lon_0-lon
        dist_lat[i] = lat_0-lat
        target_l.append(target)
        patch_l.append(edges1C[x_i-w:x_i+w,y_i-w:y_i+w])  
        o_x[i] = x_i
        o_y[i] = y_i
        t_x[i] = x_i_0
        t_y[i] = y_i_0
        # For referencing:
        origin_x[i] = x_i*fact_x
        origin_y[i] = y_i*fact_y
        target_lon[i] = lon_0
        target_lat[i] = lat_0
    return dist, origin_x, origin_y, target_lon, target_lat, o_x, o_y, t_x, t_y, RECC_l, target_l, patch_l, cv

def remove_outliers(conf, dist, origin_x, origin_y, target_lon, target_lat, o_x, o_y, t_x, t_y, cv):
    size1 = len(dist)
    indices = np.where(cv<=40)[0]
    dist       = dist[~indices]
    origin_x   = origin_x[~indices]
    origin_y   = origin_y[~indices]
    target_lon = target_lon[~indices]
    target_lat = target_lat[~indices]
    o_x        = o_x[~indices]
    o_y        = o_y[~indices]
    t_x        = t_x[~indices]
    t_y        = t_y[~indices]
    size2=len(dist)
    if   conf == 95:
        s = 5.991
    elif conf == 90:
        s = 4.605
    elif conf == 80:
        s = 3.219
    elif conf == 75:
        s = 2.770
    elif conf == 50:
        s = 1.388
    d_x = t_x - o_x
    d_y = t_y - o_y
    d_x_m = d_x - np.median(d_x)
    d_y_m = d_y - np.median(d_y)        
    indices = ((d_x_m/sqrt(np.var(d_x_m)))**2 + (d_y_m/sqrt(np.var(d_y_m)))**2 >= s)    
    dist       = dist[~indices]
    origin_x   = origin_x[~indices]
    origin_y   = origin_y[~indices]
    target_lon = target_lon[~indices]
    target_lat = target_lat[~indices]
    o_x        = o_x[~indices]
    o_y        = o_y[~indices]
    t_x        = t_x[~indices]
    t_y        = t_y[~indices]
    size3=len(dist)
    print("Removed "+str(size1-size2)+" outliers based on CV score, and "+str(size2-size3)+" outliers based on 2D confidence interval. ("+str(size3)+"/"+str(size1)+")")      
    gcplist = " "
    for k in range(len(origin_x)):
        gcplist = gcplist+"-gcp "+str(origin_y[k])+" "+str(origin_x[k])+" "+str(target_lon[k])+" "+str(target_lat[k])+" "        
    return gcplist, dist, origin_x, origin_y, target_lon, target_lat, o_x, o_y, t_x, t_y
      
def georeference(wdir,path,file,gcplist):
    print("Georeferencing image...")
    path1 = wdir+"\\temp.tif"
    path2 = wdir+"\\"+file+"_adjusted.tif"
    if os.path.isfile(path1.replace("\\","/")):
        os.remove(path1)
    if os.path.isfile(path2.replace("\\","/")):
        os.remove(path2)
    os.system("gdal_translate -a_srs EPSG:4326 -of GTiff"+gcplist+"\""+path+"\" \""+path1+"\"")
    print("Succesful translate, warping...")
    os.system("gdalwarp -r cubicspline -tps -co COMPRESS=NONE \""+path1+"\" \""+path2+"\"")    
    
