"""
/***************************************************************************
 snapshot class write sv image and geolocate snapshot
                              -------------------
        begin                : 2014-03-29
        copyright            : (C) 2014 enrico ferreguti
        email                : enricofer@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# Import the PyQt and QGIS libraries

from PyQt5 import Qt, QtCore, QtWidgets, QtGui
from qgis import core, utils, gui
from string import digits
from .go2streetviewDialog import snapshotNotesDialog
from osgeo import ogr
#from .reversegeocoder import ReverseGeocoder
from urllib.error import URLError

import resources_rc
import webbrowser
from urllib.request import urlopen
import string
import os
import datetime
import osgeo.ogr, osgeo.osr
import os.path

class snapShot():

    def __init__(self,parentInstance):
       # Save reference to the QGIS interface
       # Save reference to QWebView with Streetview application
        self.parent = parentInstance
        self.webview = parentInstance.view.SV
        self.iface = parentInstance.iface
        self.canvas = self.iface.mapCanvas()
        self.path = os.path.dirname( os.path.abspath( __file__ ) )
        self.annotationsDialog = snapshotNotesDialog()
        self.annotationsDialog.setWindowTitle("Custom snapshot notes")
        self.annotationsDialog.hide()
        self.annotationsDialog.pushButton.clicked.connect(self.returnAnnotationsValue)
        self.GeocodingServerUp = True
        self.cb = QtWidgets.QApplication.clipboard()
        #self.featureIndex = 0

    #method to define session directory and create if not present
    def sessionDirectory(self):
        path = os.path.dirname( os.path.abspath( __file__ ) )
        #datetime.datetime.now().strftime("%Y-%m-%d")
        sDir = os.path.join(self.path,'snapshots')
        if not os.path.isdir(sDir):
            os.makedirs(sDir)
        return sDir
    
    def setCurrentPOV(self):
        return {k:str(v) for k,v in self.parent.actualPOV.items()}

    # setup dialog for custom annotation
    def getAnnotations(self):
        self.annotationsDialog.label.setText(self.type.capitalize() + ":"+datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" "+self.pov['lon']+"E "+self.pov['lat']+"N")
        self.annotationsDialog.textEdit.clear()
        self.annotationsDialog.show()
        self.annotationsDialog.raise_()
        self.annotationsDialog.textEdit.setFocus()

    # landing method from ok click of annotation dialog
    def returnAnnotationsValue(self):
        self.snapshotNotes = self.annotationsDialog.textEdit.toPlainText ()
        self.snapshotNotes = self.snapshotNotes.replace("'","")
        self.snapshotNotes = self.snapshotNotes.replace('"',"")
        self.annotationsDialog.hide()
        self.saveShapeFile()
        if self.annotationsDialog.textEdit.toPlainText ()[0:1] == '#':
            self.saveImg(path = os.path.join(self.sessionDirectory(),self.annotationsDialog.textEdit.toPlainText()[1:]+'.jpg'))

    # landing method from take snapshot button"
    def saveSnapShot(self, type):
        self.pov = self.setCurrentPOV()
        self.type = type
        self.getAnnotations()

    # method to save google image to local file
    def saveImg(self,path = None):
        urlimg="http://maps.googleapis.com/maps/api/streetview?size=640x400&location="+self.pov['lat']+","+self.pov['lon']+"&heading="+self.pov['heading']+"&pitch="+self.pov['pitch']+"&sensor=false&key="+self.parent.APIkey
        #print urlimg
        if path:
            self.file_name = path
        else:
            self.file_name = os.path.join(self.sessionDirectory(),'streetview-'+self.pov['lat'].replace(".","_")+'-'+self.pov['lon'].replace(".","_")+"-"+self.pov['heading'].replace(".","_")+'-'+self.pov['pitch'].replace(".","_")+'.jpg')
        core.QgsMessageLog.logMessage(self.file_name, tag="go2streetview", level=core.Qgis.Info)
        u = urlopen(urlimg)
        f = open(self.file_name, 'wb')
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break
            file_size_dl += len(buffer)
            f.write(buffer)
        f.close()

    def getGeolocationInfo(self):
        self.pov = self.setCurrentPOV()
        return self.pov

    # procedure to create shapefile log
    def createShapefile(self,path):
        fields = core.QgsFields()
        fields.append(core.QgsField("date", QtCore.QVariant.String))
        fields.append(core.QgsField("lon", QtCore.QVariant.String))
        fields.append(core.QgsField("lat", QtCore.QVariant.String))
        fields.append(core.QgsField("heading", QtCore.QVariant.String))
        fields.append(core.QgsField("pitch", QtCore.QVariant.String))
        fields.append(core.QgsField("address", QtCore.QVariant.String))
        fields.append(core.QgsField("notes", QtCore.QVariant.String))
        fields.append(core.QgsField("url", QtCore.QVariant.String, len=250))
        fields.append(core.QgsField("type", QtCore.QVariant.String, len=8))
        srs = core.QgsCoordinateReferenceSystem ()
        srs.createFromProj4 ("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs")
        writer = core.QgsVectorFileWriter(path, "ISO 8859-1", fields,  core.QgsWkbTypes.Point, srs, "ESRI Shapefile")
        del writer

    # procedure to store image and write log
    def saveShapeFile(self):
        zoom = float(self.pov['zoom'])
        fov = 3.9018*pow(zoom,2) - 42.432*zoom + 123
        urlimg="http://maps.googleapis.com/maps/api/streetview?size=600x400&location="+self.pov['lat']+","+self.pov['lon']+"&heading="+self.pov['heading']+"&pitch="+self.pov['pitch']+"&sensor=false"+"&fov="+str(fov)+"&key="+self.parent.APIkey
        self.cb.setText(urlimg)
        sfPath=os.path.join(self.sessionDirectory(),"Streetview_snapshots_log.shp")
        if not os.path.isfile(sfPath):
            self.createShapefile(sfPath)
        vlayer = core.QgsVectorLayer(sfPath, "Streetview_snapshots_log", "ogr")

        if not "type" in [field.name() for field in vlayer.fields()]:
            res = vlayer.dataProvider().addAttributes([core.QgsField("type", QtCore.QVariant.String)])
            vlayer.updateFields()

            for feat in vlayer.getFeatures():
                if not feat["type"]:
                    feat.setAttribute('type', 'snapshot')
                    attrs = { 8 : "snapshot",}
                    vlayer.dataProvider().changeAttributeValues({ feat.id() : attrs })

        testIfLayPresent = None
        for lay in self.canvas.layers():
            if lay.name() == "Streetview_snapshots_log":
                testIfLayPresent = True
        if not testIfLayPresent:
            vlayer.loadNamedStyle(os.path.join(self.path,"snapshotStyle.qml"))
            #self.iface.actionFeatureAction().trigger()
            core.QgsProject.instance().addMapLayer(vlayer)
            set=QtCore.QSettings()
            set.setValue("/qgis/showTips", True)
        feat = core.QgsFeature()

        lon = self.pov['dlon'] if self.type == "digitize" else self.pov['lon']
        lat = self.pov['dlat'] if self.type == "digitize" else self.pov['lat']

        print (self.pov)

        feat.initAttributes(9)
        feat.setAttribute(0,datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        feat.setAttribute(1,lon)
        feat.setAttribute(2,lat)
        feat.setAttribute(3,None if self.type == "digitize" else self.pov['heading'])
        feat.setAttribute(4,None if self.type == "digitize" else self.pov['pitch'])
        feat.setAttribute(5,self.pov['address'])#self.getAddress())
        feat.setAttribute(6,self.snapshotNotes)
        #feat.setAttribute(7,self.file_name)
        feat.setAttribute(7,QtCore.QUrl(urlimg).toString())
        feat.setAttribute(8,self.type)
        feat.setGeometry(core.QgsGeometry.fromPointXY(core.QgsPointXY(float(lon), float(lat))))
        vlayer.startEditing()
        vlayer.addFeatures([feat])
        vlayer.commitChanges()
        if self.canvas.isCachingEnabled():
            vlayer.triggerRepaint()
        else:
            self.canvas.refresh()

        if self.type == "digitize":
            js = "this.addDigitizeMarker(%s,%s)" % (self.pov['dlon'], self.pov['dlat'])
            self.parent.view.SV.page().runJavaScript(js)
            self.parent.view.BE.page().runJavaScript(js)
        
        self.canvas.zoomScale(self.canvas.scale()-0.0001) 
