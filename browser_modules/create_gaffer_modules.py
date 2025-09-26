# -*- coding: utf-8 -*-
import json 
import os

from Katana import UI4, NodegraphAPI, DrawingModule, Nodes3DAPI

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class SelGafferView(QDialog):
    def __init__(self, gaffer_list, cursor_pos):
        super(SelGafferView, self).__init__()
        self.initUI()
        self.move(cursor_pos)            
        self.add_item(gaffer_list)
    
        self.listwidget.itemDoubleClicked.connect(self.list_double_click)    
                
                
    def initUI(self):
        self.setWindowTitle('Select GafferThree')
        self.setMinimumWidth(100)
        self.setMinimumHeight(130)        

        main_layout = QVBoxLayout(self)
        line_layout = QHBoxLayout()
        self.listwidget = QListWidget(self)
        self.listwidget.setStyleSheet("font-size: 11pt")
        self.listwidget.setSpacing(1)        
        line_layout.addWidget(self.listwidget)
        main_layout.addLayout(line_layout)


    def add_item(self, g_list):
        for g in g_list:        
            name = g.getName()
            self.listwidget.addItem(name)
            
            
    def list_double_click(self, item):
        if not item:
            self.return_item = ''
            self.reject()
        else:
            self.return_item = item.text()
            self.accept()

        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.return_item = ''
            self.reject()
            
            
    def showModal(self):
        result = self.exec_()
        return result, self.return_item


#
# SelImageFile  ==============================================================
#


class SelImageFile(QDialog):
    def __init__(self, json_data, cursor_pos, renderer):
        super(SelImageFile, self).__init__()
        self.init_ui()
        self.set_layout()
        self.move(cursor_pos)                
        self.json = json_data       
        self.renderer =  renderer
        #
        self.add_category_item(json_data)
        self.set_name_path(None, None)   

        self.colorspace_listwidget.currentItemChanged.connect(self.set_name_path)
        self.ext_listwidget.currentItemChanged.connect(self.set_name_path)
        self.size_listwidget.currentItemChanged.connect(self.set_name_path)
        self.name_listwidget.itemClicked.connect(self.set_image_view)
        self.OK_Button.clicked.connect(self.onOKButtonClicked)
        self.cancel_botton.clicked.connect(self.onCancelButtonClicked)
        print renderer
        

    def  init_ui(self):
        self.setWindowTitle('Select HDRI')           
        self.setMinimumSize(500, 300)   
        self.resize(500, 300)             
        
        
    def set_layout(self):
        main_layout = QVBoxLayout(self)
        category_layout = QHBoxLayout()        
        colorspace_layout = QVBoxLayout()
        self.colorspace_label = QLabel(self)
        self.colorspace_label.setText('Color Space')
        colorspace_layout.addWidget(self.colorspace_label)        
        self.colorspace_listwidget = QListWidget(self)
        colorspace_layout.addWidget(self.colorspace_listwidget)
        category_layout.addLayout(colorspace_layout)        
        ext_layout = QVBoxLayout()
        self.ext_label = QLabel(self)
        self.ext_label.setText('Ext')
        ext_layout.addWidget(self.ext_label)        
        self.ext_listwidget = QListWidget(self)
        ext_layout.addWidget(self.ext_listwidget)
        category_layout.addLayout(ext_layout)        
        size_layout = QVBoxLayout()
        self.size_label = QLabel(self)
        self.size_label.setText('Size')
        size_layout.addWidget(self.size_label)        
        self.size_listwidget = QListWidget(self)
        size_layout.addWidget(self.size_listwidget)                
        category_layout.addLayout(size_layout)
        main_layout.addLayout(category_layout)   
        #         
        file_layout = QHBoxLayout()        
        name_layout = QVBoxLayout()
        self.name_label = QLabel(self)
        self.name_label.setText('Name')
        name_layout.addWidget(self.name_label)        
        self.name_listwidget = QListWidget(self)
        self.name_listwidget.setSelectionMode(QListWidget.MultiSelection)
        name_layout.addWidget(self.name_listwidget)
        file_layout.addLayout(name_layout)        
        view_layout = QVBoxLayout()
        self.view_label = QLabel(self)
        self.view_label.setText('View')
        view_layout.addWidget(self.view_label)        
        self.view_graphics = QGraphicsView(self)
        view_layout.addWidget(self.view_graphics)
        file_layout.addLayout(view_layout)     
        main_layout.addLayout(file_layout)  
        file_layout.setStretch(0, 3)
        file_layout.setStretch(1, 2)        
        #             
        button_layout = QHBoxLayout()
        horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        button_layout.addItem(horizontalSpacer)
        self.OK_Button = QPushButton(self)
        self.OK_Button.setText('OK')
        button_layout.addWidget(self.OK_Button)
        self.cancel_botton = QPushButton(self)
        self.cancel_botton.setText('Cancel')
        button_layout.addWidget(self.cancel_botton)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        
        
    def add_category_item(self, json_data):
        color_list = json_data['asset']['variable']['colorSpace']
        ext_list = json_data['asset']['variable']['extension']
        res_list = json_data['asset']['variable']['resolutuion']                
        
        self.colorspace_listwidget.addItems(color_list)
        self.ext_listwidget.addItems(ext_list)
        self.size_listwidget.addItems(res_list)
        
        self.colorspace_listwidget.setCurrentRow(0)
        self.ext_listwidget.setCurrentRow(0)
        if self.renderer == 'prman':
            self.ext_listwidget.setCurrentRow(1)         
        self.size_listwidget.setCurrentRow(0)

        
    def set_name_path(self, current, previous):
        self.name_listwidget.clear()
            
        path =  self.json['lightSourcePath']
        color = self.colorspace_listwidget.currentItem().text()
        ext = self.ext_listwidget.currentItem().text()
        size = self.size_listwidget.currentItem().text()       
        
        current_path = os.path.join(path, color, ext, size)
        if os.path.isdir(current_path):     
            files = os.listdir(current_path)      
            files.sort()           
            self.name_listwidget.addItems(files)
            

    def set_image_view(self):
        path =  self.json['lightSourcePath']    
        json_name = self.json['name']
        size = self.size_listwidget.currentItem().text()            
        sel_items = self.name_listwidget.selectedItems()
        first_text = [item.text() for item in sel_items]
        
        if first_text:
            first_name, first_ext = os.path.splitext(first_text[-1])
            first_suffix = first_name.split(size)[-1]

            preview_path = os.path.join(path, 'preview/sample_image')
            if os.path.isdir(preview_path):    
                files = os.listdir(preview_path)     
                for i in files:
                    name, ext = os.path.splitext(i)                    
                    suffix = name.split(json_name)[-1]
                    if first_name == name:
                        preview_file = os.path.join(preview_path, i)
                        self.graphics_scene = QGraphicsScene()
                        self.pixmap = QPixmap(preview_file)
                        self.pixmap_item = QGraphicsPixmapItem(self.pixmap)
                        self.graphics_scene.addItem(self.pixmap_item)
                        self.view_graphics.setScene(self.graphics_scene)
                        self.view_graphics.fitInView(self.pixmap_item, mode=Qt.KeepAspectRatio)                        
                
        
    def onOKButtonClicked(self):
        path =  self.json['lightSourcePath']
        color = self.colorspace_listwidget.currentItem().text()
        ext = self.ext_listwidget.currentItem().text()
        size = self.size_listwidget.currentItem().text()          
        item_path = os.path.join(path, color, ext, size)
        
        sel_items = self.name_listwidget.selectedItems()
        names = [item.text() for item in sel_items] 
        
        self.return_list = []
        for name in names:
            item_file = os.path.join(item_path, name)
            if os.path.exists(item_file):
                self.return_list.append(str(item_file))
        self.accept()
        
        
    def onCancelButtonClicked(self):
        self.return_list = []
        self.reject()
        
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.return_list = []
            self.reject()
            
    
    def resizeEvent(self, event):
        if hasattr(self, 'pixmap_item'): 
            self.view_graphics.fitInView(self.pixmap_item, mode=Qt.KeepAspectRatio) 
        super(SelImageFile, self).resizeEvent(event)

                
    def showModal(self):
        result = self.exec_()
        return result, self.return_list



#
# 실행  ==============================================================
#


def create_item_in_gaffer(renderer, gaffer, json_path, ui):
    # 포지션
    point_x = ui.pos().x() + ui.rect().width()//2 - 100
    point_y = ui.pos().y() + ui.rect().height()//2 - 100            
    adjusted_pos = QtCore.QPoint(point_x, point_y)

    #check gaffer
    if len(gaffer) < 1:
        printInfo = 'GafferThree가 존재하지 않습니다.'
        QMessageBox.warning(ui, 'Warning', printInfo)        
        return    
    elif len(gaffer) == 1:
        gaffer_name = gaffer[0].getName()   
    else:  
        SGV = SelGafferView(gaffer, adjusted_pos)
        g_status, gaffer_name = SGV.showModal()
        if g_status == 0:
            return
        
    # open prman json file        
    with open(json_path, 'r') as prman_json:
        prman_data = json.load(prman_json)
        
    # open library json file        
    with open(os.path.join(str(prman_data['lightSourcePath']), 'data.json'), 'r') as library_json:
        library_data = json.load(library_json) 
        
    # get image data
    create_status = False
    mode = library_data['mode']
    if mode == 'IES':
        source_path = str(library_data['asset']['dependencies']['imageExt'])
        if source_path:                
            create_status = create_ies(source_path, gaffer_name)
    elif mode == 'Gobo':
        source_path = str(library_data['asset']['dependencies']['imageTex'])
        if source_path:        
            create_status = create_gobo(source_path, gaffer_name)
    else:
        SIF = SelImageFile(library_data, adjusted_pos, renderer)
        i_status, source_path_list = SIF.showModal()
        
        if source_path_list:
            create_status = create_hdri(source_path_list, gaffer_name)
            
    if  create_status:
        printInfo = '{}에\n정상적으로 만들어 졌습니다.'.format(gaffer_name)
        QMessageBox.information(ui, 'Create...!!', printInfo)        
        return        
    else:
        return


def create_hdri(source_path_list, gaffer_name):
    try:
        gaffer = NodegraphAPI.GetNode(gaffer_name)    
        root_package = gaffer.getRootPackage()

        rig = root_package.getChildPackage('Lgt_dome_Rig')
        if not root_package.getChildPackage('Lgt_dome_Rig'):
            rig = root_package.createChildPackage('RigPackage')
            rig.setName('Lgt_dome_Rig')
            
        cnt = 1
        for  source_path in source_path_list:
            source_name, ext = os.path.splitext(os.path.basename(source_path))

            light = rig.createChildPackage('PxrDomeLightPackage')
            light.setName(source_name)
            mat = light.getMaterialNode()
            mat.checkDynamicParameters()
            params = mat.getParameters().getChild('shaders.prmanLightParams')
            params.getChild('lightColorMap.enable').setValue(1.0, 0)
            params.getChild('lightColorMap.value').setValue(source_path, 0)
            params.getChild('lightGroup.enable').setValue(1.0, 0)
            params.getChild('lightGroup.value').setValue('dome_'+str(cnt).zfill(2), 0)

            cnt += 1
        return True
    except:
        return False    
        
        
def create_ies(source_path, gaffer_name):
    try:
        gaffer = NodegraphAPI.GetNode(gaffer_name)    
        root_package = gaffer.getRootPackage()

        rig = root_package.getChildPackage('Ies_Rig')
        if not root_package.getChildPackage('Ies_Rig'):
            rig = root_package.createChildPackage('RigPackage')
            rig.setName('Ies_Rig')
            
        source_name, ext = os.path.splitext(os.path.basename(source_path))        
            
        light = rig.createChildPackage('PxrRectLightPackage')
        light.setName(source_name)
        mat = light.getMaterialNode()
        mat.checkDynamicParameters()
        params = mat.getParameters().getChild('shaders.prmanLightParams')
        params.getChild('iesProfile.enable').setValue(1.0, 0)
        params.getChild('iesProfile.value').setValue(source_path, 0)
        params.getChild('lightGroup.enable').setValue(1.0, 0)
        params.getChild('lightGroup.value').setValue('lamp_01', 0)
        return True    
    except:
        return False    


def create_gobo(source_path, gaffer_name):
    try:
        gaffer = NodegraphAPI.GetNode(gaffer_name)    
        root_package = gaffer.getRootPackage()
        
        rig = root_package.getChildPackage('gobo_Rig')
        if not root_package.getChildPackage('gobo_Rig'):
            rig = root_package.createChildPackage('RigPackage')
            rig.setName('gobo_Rig')
            
        source_name, ext = os.path.splitext(os.path.basename(source_path))         
        light = rig.createChildPackage('PxrRectLightPackage')
        light.setName(source_name)    
        mat = light.getMaterialNode()
        mat.checkDynamicParameters()
        params = mat.getParameters().getChild('shaders.prmanLightParams')
        params.getChild('lightGroup.enable').setValue(1.0, 0)
        params.getChild('lightGroup.value').setValue('gobo_01', 0)
        
        light_filter = light.createChildPackage('PxrCookieLightFilterPackage')    
        filter_mat = light_filter.getMaterialNode()
        filter_mat.checkDynamicParameters()     
        filter_params = filter_mat.getParameters().getChild('shaders.prmanLightfilterParams')
        filter_params.getChild('map.enable').setValue(1.0, 0)
        filter_params.getChild('map.value').setValue(source_path, 0)        
            
        filter_node = light_filter.getCreateNode()
        filter_node.getParameter('transform.translate.z').setValue(-1, 0)
        return True        
    except:
        return False
        
        
        
        
        
        
