# -*- coding: utf-8 -*-
"""
Created on Wed Jul 31 09:41:31 2019

@author: wytze
"""
import gdal
import numpy as np
from mpl_toolkits.mplot3d import Axes3D #shows as unused but is needed for surf plot
import matplotlib.pyplot as plt
from scipy import stats, signal
from typing import List
from scipy import interpolate
import skgstat as skg

file = gdal.Open("C:/Users/wytze/20190603_modified.tif")
ridges = gdal.Open("C:/Users/wytze/crop_top.tif")

ridges_array = ridges.GetRasterBand(1).ReadAsArray()

band = file.GetRasterBand(1)
array = band.ReadAsArray()
projection = file.GetProjection()
gt = file.GetGeoTransform()
xsize = band.XSize
ysize = band.YSize

array[array < 0] = 0

#%% Polygon and Point class
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        
    def dist(self, p):
        return np.sqrt((self.x - p.x)**2 + (self.y - p.y)**2)
        
class Polygon:
    EXTREME = 100000000
    def __init__(self, vs: List[Point]):
        self.vs = vs
    
    """Given three colinear points p, q, r, the function checks if q lies on line segment pr
    
    :param p: start of line segment pr
    :param q: the point to check
    :param r: end of line segment pr
    :returns: True if q on line segment pr
    """
    def on_segment(self, p, q, r):
        if (q.x <= max(p.x, r.x) and q.x >= min(p.x, r.x) and q.y <= max(p.y, r.y) and q.y >= min(p.y, r.y)):
            return True
        return False
    
    """Find orientation of ordered triplet (p, q, r)
    0 --> p, q, r are colinear
    1 --> Clockwise
    2 --> Counter clockwise
    
    :param p, q, r: points of which the orientation is checked
    :returns: orientation of the given points
    """
    def orientation(self, p, q, r):
        val = (q.y - p.y) * (r.x - q.x) - (q.x - p.x) * (r.y - q.y)
        if (val == 0): 
            return 0
        return 1 if val > 0 else 2
    
    """Check if line segment p1q1 and p2q2 intersect
    
    :param p1, q1, p1, p2: the points of the line segments which are checked for intersection
    :returns: True if p1q1 and p2q2 intersect
    """
    def do_intersect(self, p1, q1, p2, q2):
        o1 = self.orientation(p1, q1, p2)
        o2 = self.orientation(p1, q1, q2)
        o3 = self.orientation(p2, q2, p1)
        o4 = self.orientation(p2, q2, q1)
        
        if (o1 != o2 and o3 != o4):
            return True
        
        if (o1 == 0 and self.on_segment(p1, p2, q1)):
            return True
        
        if (o2 == 0 and self.on_segment(p1, q2, q1)):
            return True
        
        if (o3 == 0 and self.on_segment(p2, p1, q2)):
            return True
        
        if (o4 == 0 and self.on_segment(p2, q1, q2)):
            return True
        
        return False
    
    """Check if point p is inside the n-sized polygon given by points vs
    
    :param vs: list of points which make up the polygon
    :param n: number of vertices of the polygon
    :param p: the point to be checked
    :returns: True if p lies inside the polygon
    """
    def is_inside_polygon(self, p: Point):
        if len(self.vs) < 3:
            return False
        
        extreme = Point(self.EXTREME, p.y)
        
        count = 0
        i = 0
        while True:
            next_i = (i + 1) % len(self.vs)
            
            if self.do_intersect(self.vs[i], self.vs[next_i], p, extreme):
                if self.orientation(self.vs[i], p, self.vs[next_i]) == 0:
                    return self.on_segment(self.vs[i], p, self.vs[next_i])
                count += 1
                
            i = next_i
            if i == 0:
                break
        
        return count % 2 == 1

class Polynomial_fit:
    coeff = []
    def __init__(self, x: List[Point], array, order: int):
        self.x = x
        self.order = order 
        
        n_terms = int(((self.order + 1) * (self.order + 2)) / 2)
        
        # Create matrix which describes (1, x, x^2, x*y, y, y^2) and vector for z-values in all points of x
        z = np.zeros(len(self.x))
        X = np.zeros((len(self.x), n_terms))
        
        for i in range(len(x)):
            z[i] = array[x[i].x, x[i].y]
            
            X[i, 0] = 1
            a = 1
            for k in range(1, order + 1):
                for l in range(k + 1):
                    X[i, a] = x[i].x**l * x[i].y**(k - l)
                    a += 1
        
        # Create function z = b[0] + b[1]*x + b[2]*x^2 + b[3]*x*y + b[4]*y + b[5]*y^2 + b[6]*x^3 + b[7]*x^2*y + b[8]*x*y^2 + b[9]*y^3
        # b = (X^T*X)^-1 X^T * z
        XT = X.transpose()
        self.coeff = np.linalg.inv(np.matmul(XT, X)) @ (XT @ z)
    
    def get_values_on_matrix(self, ysize, xsize):
        Z = np.zeros((ysize, xsize))
        for i in range(ysize):
            for j in range(xsize):
                a = 0
                for k in range(self.order + 1):
                    for l in range(k + 1):
                        Z[i, j] += self.coeff[a] * i**l * j**(k - l)
                        a += 1
        return Z
        

    
def create_tiff(array, gt, projection, dest: str):
    driver = gdal.GetDriverByName('GTiff')
    tiff = driver.Create(dest, array.shape[1], array.shape[0], 1, gdal.GDT_Int16)
    tiff.SetGeoTransform(gt)
    tiff.SetProjection(projection)
    tiff.GetRasterBand(1).WriteArray(array)
    tiff.GetRasterBand(1).FlushCache()
    tiff = None
    
#%% variance
x1 = (51.73861232, 4.38036677) #top-left
x2 = (51.73829906, 4.38376774) #top-right
x3 = (51.73627495, 4.38329311) #bottom-right
x4 = (51.73661151, 4.37993097) #bottom-left

x1_i = Point(int(abs(np.floor((x1[0] - gt[3])/gt[1]))), int(abs(np.floor((x1[1] - gt[0])/gt[5]))))
x2_i = Point(int(abs(np.floor((x2[0] - gt[3])/gt[1]))), int(abs(np.floor((x2[1] - gt[0])/gt[5]))))
x3_i = Point(int(abs(np.floor((x3[0] - gt[3])/gt[1]))), int(abs(np.floor((x3[1] - gt[0])/gt[5]))))
x4_i = Point(int(abs(np.floor((x4[0] - gt[3])/gt[1]))), int(abs(np.floor((x4[1] - gt[0])/gt[5]))))

poly = Polygon([x1_i, x2_i, x3_i, x4_i])

xstep = 50
ystep = 50
sum1 = 0
sum2 = 0
n = 0

for i in range(int(ysize/ystep)):
    for j in range(int(xsize/xstep)):
        if poly.is_inside_polygon(Point(i * ystep, j * xstep)) and ridges_array[i][j] == 0:
            sum1 += array[i * ystep][j * xstep]
            n += 1

mean = sum1/n
for i in range(int(ysize/ystep)):
    for j in range(int(xsize/xstep)):
        if poly.is_inside_polygon(Point(i * ystep, j * xstep)) and ridges_array[i][j] == 0:
            sum2 += (array[i * ystep][j * xstep] - mean)**2

variance = sum2 / (n - 1)

#%% semivariogram
x1 = (52.27874252, 4.53404572) #top-left
x2 = (52.27856259, 4.53438068) #top-right
x3 = (52.27813766, 4.53389149) #bottom-right
x4 = (52.27826056, 4.53364649) #bottom-left

x1_i = Point(int(abs(np.floor((x1[0] - gt[3])/gt[1]))), int(abs(np.floor((x1[1] - gt[0])/gt[5]))))
x2_i = Point(int(abs(np.floor((x2[0] - gt[3])/gt[1]))), int(abs(np.floor((x2[1] - gt[0])/gt[5]))))
x3_i = Point(int(abs(np.floor((x3[0] - gt[3])/gt[1]))), int(abs(np.floor((x3[1] - gt[0])/gt[5]))))
x4_i = Point(int(abs(np.floor((x4[0] - gt[3])/gt[1]))), int(abs(np.floor((x4[1] - gt[0])/gt[5]))))

poly = Polygon([x1_i, x2_i, x3_i, x4_i])

file = gdal.Open("C:/Users/wytze/OneDrive/Documents/vanBoven/Tulips/DEM/Achter_de_rolkas-20190420-DEM.tif")

band = file.GetRasterBand(1)
array = band.ReadAsArray()
projection = file.GetProjection()
gt = file.GetGeoTransform()
xsize = band.XSize
ysize = band.YSize

array[array == np.amin(array)] = 0

xstep = 2
xmax = 400
x = range(xstep, xmax, xstep)
gamma = np.zeros(len(x))

for a in x:
    sum0 = 0
    V = 0
    for i in range(0, ysize, a):
        for j in range(0, xsize, a):
            if i + a < ysize and array[i][j] != 0 and array[i][j] and array[i + a][j]:
                sum0 += (array[i][j] - array[i + a][j])**2
                V += 1
    gamma[x.index(a)] = sum0 /(2 * V) if V != 0 else 0
    
# =============================================================================
# for i in range(1, len(gamma) - 1):
#     if gamma[i] > 0.5:
#         gamma[i] = 0.5 * (gamma[i - 1] + gamma[i + 1])
# 
# gamma[gamma > 0.1] = 0
# =============================================================================
plt.plot(x, gamma)

coeff = np.polyfit(x, gamma, 2)
plt.plot(x, coeff[2] + coeff[1] *x + coeff[0] * np.square(x))
plt.show()


#%%
z = []
coord = []
for i in range(0, ysize, 50):
    for j in range(0, xsize, 50):
        if array[i][j] != 0:
            coord.append([i, j])
            z.append(array[i, j])

V = skg.Variogram(coordinates = coord, values = z)
print(V)


