#!/usr/bin/env python
# -*- coding: utf8 -*-
import sys
import os
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from lxml import etree
import codecs
import numpy as np
from math import acos, cos, sin, pi, sqrt
from libs.constants import DEFAULT_ENCODING

import urllib.parse

TXT_EXT = '.txt'
ENCODE_METHOD = DEFAULT_ENCODING

class KITTIWriter:

    def __init__(self, foldername, filename, imgSize, databaseSrc='Unknown', localImgPath=None):
        self.foldername = foldername
        self.filename = filename
        self.databaseSrc = databaseSrc
        self.imgSize = imgSize
        self.boxlist = []
        self.localImgPath = localImgPath
        self.verified = False

    def addBndBox(self, xmin, ymin, xmax, ymax, rotation, name, difficult, content):
        # bndbox = {'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax}
        bndbox = {'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax, 'rotation': rotation}
        bndbox['name'] = name
        bndbox['difficult'] = difficult
        bndbox['content'] = content
        self.boxlist.append(bndbox)

    def BndBox2KittiLine(self, box, classList=[]):
        xmin = box['xmin']
        xmax = box['xmax']
        ymin = box['ymin']
        ymax = box['ymax']
        rotation = box['rotation']
        content = box['content']

        cosval = abs(cos(rotation))
        sinval = abs(sin(rotation))
        a = np.array([[cosval, sinval], [sinval, cosval]])
        b = np.array([xmax - xmin, ymax - ymin])
        size = np.linalg.solve(a, b)

        xcen = float((xmin + xmax)) / 2
        ycen = float((ymin + ymax)) / 2

        w = float((size[0]))
        h = float((size[1]))

        rotation = float(rotation)

        # PR387
        boxName = box['name']
        if boxName not in classList:
            classList.append(boxName)

        classIndex = classList.index(boxName)

        content = urllib.parse.quote(content)

        return classIndex, xcen, ycen, w, h, rotation, content

    def save(self, classList=[], targetFile=None):

        out_file = None #Update yolo .txt
        out_class_file = None   #Update class list .txt

        if targetFile is None:
            out_file = open(
            self.filename + TXT_EXT, 'w', encoding=ENCODE_METHOD)
            classesFile = os.path.join(os.path.dirname(os.path.abspath(self.filename)), "classes.txt")
            out_class_file = open(classesFile, 'w')

        else:
            out_file = codecs.open(targetFile, 'w', encoding=ENCODE_METHOD)
            classesFile = os.path.join(os.path.dirname(os.path.abspath(targetFile)), "classes.txt")
            out_class_file = open(classesFile, 'w')


        for box in self.boxlist:
            classIndex, xcen, ycen, w, h, rotation, content = self.BndBox2KittiLine(box, classList)
            # print (classIndex, xcen, ycen, w, h)
            out_file.write("%d %.6f %.6f %.6f %.6f %.6f %s\n" % (classIndex, xcen, ycen, w, h, rotation, content))

        # print (classList)
        # print (out_class_file)
        for c in classList:
            out_class_file.write(c+'\n')

        out_class_file.close()
        out_file.close()



class KittiReader:

    def __init__(self, filepath, image, classListPath=None):
        # shapes type:
        # [labbel, [(x1,y1), (x2,y2), (x3,y3), (x4,y4)], rotation, color, color, difficult]
        self.shapes = []
        self.filepath = filepath

        if classListPath is None:
            dir_path = os.path.dirname(os.path.realpath(self.filepath))
            self.classListPath = os.path.join(dir_path, "classes.txt")
        else:
            self.classListPath = classListPath

        # print (filepath, self.classListPath)

        classesFile = open(self.classListPath, 'r')
        self.classes = classesFile.read().strip('\n').split('\n')

        # print (self.classes)

        imgSize = [image.height(), image.width(),
                      1 if image.isGrayscale() else 3]

        self.imgSize = imgSize

        self.verified = False
        # try:
        self.parseYoloFormat()
        # except:
            # pass

    def getShapes(self):
        return self.shapes

    def addShape(self, label, xmin, ymin, xmax, ymax, rotation, difficult, content):

        points = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
        self.shapes.append((label, points, rotation, None, None, difficult, content))

    def kittiLine2Shape(self, classIndex, xcen, ycen, w, h, rotation, content):
        label = self.classes[int(classIndex)]

        xmin = max(float(xcen) - float(w) / 2, 0)
        xmax = min(float(xcen) + float(w) / 2, self.imgSize[1])
        ymin = max(float(ycen) - float(h) / 2, 0)
        ymax = min(float(ycen) + float(h) / 2, self.imgSize[0])

        rotation = float(rotation)

        context = urllib.parse.unquote(content)

        return label, xmin, ymin, xmax, ymax, rotation, content

    def parseYoloFormat(self):
        bndBoxFile = open(self.filepath, 'r')
        for bndBox in bndBoxFile:
            data = bndBox.split(' ')
            if len(data) == 6:
                classIndex, xcen, ycen, w, h, rotation = data
                content = ''
            elif len(data) == 7:
                classIndex, xcen, ycen, w, h, rotation, content = data
                
            label, xmin, ymin, xmax, ymax, rotation, content = self.kittiLine2Shape(classIndex, xcen, ycen, w, h, rotation, content)

            # Caveat: difficult flag is discarded when saved as yolo format.
            self.addShape(label, xmin, ymin, xmax, ymax, rotation, False, content)
