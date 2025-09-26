# -*- coding: utf-8 -*-
import os
import re
import json
import shutil
import subprocess
import yaml

from pprint import pprint
from collections import OrderedDict
from functools import partial

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import browser_modules_init
reload(browser_modules_init)


class UpdateCategory(QDialog):
    def __init__(self, cursor_pos, sel_swatch):
        super(UpdateCategory, self).__init__()
        self.initUI()
        self.move(cursor_pos)
        # btn
        self.OK_Button.clicked.connect(self.onOKButtonClicked)
        self.cancel_botton.clicked.connect(self.onCancelButtonClicked)   
        self.category.change_categories.connect(self.update_category)                        
        # get datas
        self.swatch = sel_swatch                         
        self.get_json() 
        self.get_category()


    def initUI(self):
        self.setWindowTitle('Change Category')
        self.setMinimumSize(750, 120)

        layout = QVBoxLayout()
        grid_layout = QGridLayout()
        self.name_label = QLabel(self)
        self.name_label.setText('Asset Name')
        grid_layout.addWidget(self.name_label, 0, 0, 1, 1)
        self.name_edit = QLabel(self)
        self.name_edit.setText('-9999')
        grid_layout.addWidget(self.name_edit, 0, 1, 1, 1)
        
        self.ori_category_label = QLabel()
        self.ori_category_label.setText('Category')
        grid_layout.addWidget(self.ori_category_label, 1, 0, 1, 1)
        self.ori_category_edit = QLabel(self)
        self.ori_category_edit.setText('-9999')
        grid_layout.addWidget(self.ori_category_edit, 1, 1, 1, 1)        

        self.new_category_label = QLabel()
        self.new_category_label.setText('New Category')
        grid_layout.addWidget(self.new_category_label, 2, 0, 1, 1)
        self.new_category_layout = QVBoxLayout()
        grid_layout.addLayout(self.new_category_layout, 2, 1, 1, 1)
        self.category = CreateCategory(self)

        self.button_layout = QHBoxLayout()
        horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.button_layout.addItem(horizontalSpacer)
        self.OK_Button = QPushButton(self)
        self.OK_Button.setText('OK')
        self.button_layout.addWidget(self.OK_Button)
        self.cancel_botton = QPushButton(self)
        self.cancel_botton.setText('Cancel')
        self.button_layout.addWidget(self.cancel_botton)
        grid_layout.addLayout(self.button_layout, 3, 1, 1, 1)

        layout.addLayout(grid_layout)
        self.setLayout(layout)

        
    def update_category(self, final_path):
        self.final_category =  final_path        
        

    def get_json(self):
        self.prman_json_path = self.swatch._asset.jsonFilePath()     
       
        # open prman json file        
        with open(self.prman_json_path, 'r') as p_json:
            self.prman_json = json.load(p_json, object_pairs_hook=OrderedDict)                   

        # open library json file     
        self.library_json_path = os.path.join(str(self.prman_json['lightSourcePath']), 'data.json')
        with open(self.library_json_path, 'r') as l_json:
            self.library_json = json.load(l_json, object_pairs_hook=OrderedDict) 
               
        self.name_edit.setText(self.library_json['name'])

        
        
    def get_category(self):
        fixed_path = os.path.dirname(self.category.IMAGE_SOURCE_PATH)
        swatch_path = os.path.dirname(self.library_json['lightSourcePath'])
        category_name = os.path.relpath(swatch_path, fixed_path)
        category_list = category_name.split('/')
        
        self.ori_category_edit.setText(category_name)
        
        #
        for cnt in range(len(category_list)):
            if cnt == 0:
                self.category.path_category_combobox.blockSignals(True)            
                self.category.path_category_combobox.setCurrentText(category_list[cnt])         
                self.category.path_category_combobox.blockSignals(False)            

            elif cnt == 1:            
                if category_list[cnt] == 'HDRI':   
                    self.category.browse_folder(self.category.category_combobox)                     
                else:
                    self.category.category_combobox.setCurrentText(category_list[cnt])         
            else:  
                num = str(cnt - 1).zfill(2)        
                object_name = 'store_combobox_{0}'.format(num)    
                find_object = self.findChild(QComboBox, object_name)      
                if find_object:
                    find_object.setCurrentText(category_list[cnt])             

        
    def convert_path(self):
        self.old_library_path = self.library_json['lightSourcePath']          
        self.old_prman_path = self.library_json['PrmanBrowserPath']            
    
        old_cateogories =  self.ori_category_edit.text()
        second_category = self.category.path_category_combobox.currentText()
        new_categories = os.path.join(second_category, self.final_category)

        prman_path = self.category.PRMAN_BROWSER_PATH
        final_category = self.final_category
        
        final_category_split = final_category.split('/')
        fisrt_category = final_category_split[0]
        else_category = '/'.join(final_category_split[1:])
        
        if fisrt_category == 'LightFilter':
            fisrt_category = 'LightRigs'                
        elif fisrt_category == 'HDRI':
            fisrt_category = 'EnvironmentMaps'        

        # library_path              
        self.new_library_path = self.old_library_path.replace(old_cateogories, new_categories)    
        # prman_path 
        self.new_prman_path = os.path.join(prman_path, 
                                                            fisrt_category, 
                                                            second_category, 
                                                            else_category,
                                                            os.path.basename(self.old_prman_path))                                      
    

    def convert_prman_folder(self):
        self.prman_json['PrmanBrowserPath'] = self.prman_json['PrmanBrowserPath'].replace(self.old_prman_path, self.new_prman_path) 
        self.prman_json['lightSourcePath'] = self.prman_json['lightSourcePath'].replace(self.old_library_path, self.new_library_path)        
        self.prman_json['RenderManAsset']['storage']['path'] = self.prman_json['RenderManAsset']['storage']['path'].replace(self.old_prman_path, self.new_prman_path)    
                 
        with open(self.prman_json_path, 'w') as p_w_json:
            json.dump(self.prman_json, p_w_json, ensure_ascii=False, indent=4, encoding='utf-8')              

        shutil.move(self.old_prman_path, self.new_prman_path)        


    def convert_library_folder(self):
        self.library_json['PrmanBrowserPath'] = self.library_json['PrmanBrowserPath'].replace(self.old_prman_path, self.new_prman_path) 
        self.library_json['lightSourcePath'] = self.library_json['lightSourcePath'].replace(self.old_library_path, self.new_library_path)        
        self.library_json['asset']['dependencies']['imageExt'] = self.library_json['asset']['dependencies']['imageExt'].replace(self.old_library_path, self.new_library_path) 
        self.library_json['asset']['dependencies']['imageTex'] = self.library_json['asset']['dependencies']['imageTex'].replace(self.old_library_path, self.new_library_path)        
        
        with open(self.library_json_path, 'w') as l_w_json: 
            json.dump(self.library_json, l_w_json, ensure_ascii=False, indent=4, encoding='utf-8')  
            
        shutil.move(self.old_library_path, self.new_library_path)        
        
        
    def onOKButtonClicked(self):
        category_num = self.category.get_category_len()
        if category_num < 3:
            QMessageBox.warning(self, 'Warning', 'Category가 너무 짧습니다.')     
            return 

        self.convert_path()        
        self.convert_prman_folder()    
        self.convert_library_folder()

        self.accept()


    def onCancelButtonClicked(self):
        self.reject()


    def showModal(self):
        result = self.exec_()


#
# CreateCategory  ==============================================================
#


class CreateCategory(QObject):
    PRMAN_BROWSER_PATH = browser_modules_init.get_prman_browser_path()
    IMAGE_SOURCE_PATH = browser_modules_init.get_image_source_path()
    SHOW_SOURCE_PATH = browser_modules_init.get_show_source_path()
    USER_SOURCE_PATH = browser_modules_init.get_user_source_path()   
    
    change_categories = pyqtSignal(str)

    def __init__(self, parent):
        super(CreateCategory, self).__init__(parent)
        self.parent = parent
        
        self.initUI()
        self.set_category_item()
        self.btn_triggers()        

                
    def initUI(self):
            # 버튼 레이아웃
            self.category_layout = QHBoxLayout()            
            self.path_category_combobox = QComboBox(self.parent)
            self.path_category_combobox.setObjectName("path_category")                           
            self.category_layout.addWidget(self.path_category_combobox)                        
            self.category_combobox = QComboBox(self.parent)
            self.category_combobox.setObjectName("category_combobox_00")    
            self.category_layout.addWidget(self.category_combobox)                    
            self.parent.new_category_layout.addLayout(self.category_layout)


    def btn_triggers(self):
        self.category_combobox.currentIndexChanged.connect(
            partial(self.browse_folder, self.category_combobox))
        self.path_category_combobox.currentIndexChanged.connect(
            partial(self.browse_folder, self.category_combobox))


    def set_category_item(self):        
        self.category_combobox.addItem('HDRI', 'HDRI')
        self.category_combobox.addItem('LightFilter', 'LightFilter')
        
        self.path_category_combobox.addItem('WW', CreateCategory.IMAGE_SOURCE_PATH)
        self.path_category_combobox.addItem('Show', CreateCategory.SHOW_SOURCE_PATH)
        self.path_category_combobox.addItem('User', CreateCategory.USER_SOURCE_PATH)              
        

    def browse_folder(self, parent_combobox):
        # data
        current_category_name = self.path_category_combobox.currentData()
        parnet_text = parent_combobox.currentText()
        parent_category = parent_combobox.currentData()
        parent_path = os.path.join(current_category_name, parent_category) 
        parent_name = parent_combobox.objectName()
        parent_num = int(re.search(r'_(\d+)$', parent_name).group(1))
        object_num = str(parent_num + 1).zfill(2)

        object_name = 'store_combobox_{0}'.format(object_num)
        
        # 최종 경로
        final_category = parent_combobox.currentData()            
        if parnet_text == '* New Category':
            path_status, new_categoty_name = self.create_new_category_path(parent_combobox, parent_category, parent_path)
            if path_status:
                object_name = parent_name #새 카테고리 추가가 아니라 다시 원래것을 불러오기 위함
                self.del_child_object(object_name)  
                self.add_store_combobox(object_name, parent_category, parent_path)
                self.store_combobox.setCurrentText(str(new_categoty_name))
                final_category =  os.path.join(final_category, new_categoty_name)
            else:
                self.store_combobox.setCurrentText(str(new_categoty_name))        
        elif parnet_text == '':
            self.del_child_object(object_name)         
        else:
            if os.path.isdir(parent_path):                         
                self.del_child_object(object_name)              
                self.add_store_combobox(object_name, parent_category, parent_path)       

        # emit singnal                 
        self.change_categories.emit(final_category)                

        
    def del_child_object(self, object_name):
        # 카테고리 꼬임을 방지하기 위해 지웠다가 다시 생성
        current_num = int(re.search(r'_(\d+)$', object_name).group(1))

        num = str(current_num).zfill(2)        
        while True:
            object_name = 'store_combobox_{0}'.format(num)    
            find_object = self.parent.findChild(QComboBox, object_name)      

            if find_object is None:
                break 

            self.category_layout.removeWidget(find_object)
            find_object.deleteLater()                                 
            num = str(int(num) + 1).zfill(2)


    def add_store_combobox(self, object_name, parent_category, parent_path):
        # 경로를 바탕으로 카테고리 생성         
        self.store_combobox = QComboBox(self.parent)           
        self.store_combobox.setObjectName(object_name)
        self.category_layout.addWidget(self.store_combobox)                

        # 빈 리스트 추가             
        self.store_combobox.addItem('', parent_category)                           
        # 하위 폴더 카테고리로 등록            
        sub_folders = self.get_sub_folders(parent_path) #하위 폴더 리스트 구하기
        if sub_folders:                                  
            for sub_folder in sub_folders:
                sub_folder_path = os.path.join(parent_path, sub_folder)      
                sub_category_path = os.path.join(parent_category, sub_folder)                 
                check_json = self.if_contain_json(sub_folder_path) 
                if not check_json: # json을 가진 데이터 폴더는 카테고리 리스트에서 제외시키기                    
                    self.store_combobox.addItem(sub_folder, sub_category_path)                                                
        # 새로운 카테고리
        self.store_combobox.addItem('* New Category', parent_category)               
        
        # connect                              
        self.store_combobox.currentIndexChanged.connect(
            partial(self.browse_folder, self.store_combobox))      
        
          
    def create_new_category_path(self, parent_combobox, parent_category, parent_path):
        win = SubWindow(self.parent, parent_category)
        r = win.showModal()            
        if r[0]:
            items = [str(parent_combobox.itemText(i).lower()) for i in range(parent_combobox.count())]
            new_path = os.path.join(parent_path, r[1])
            if not os.path.exists(new_path) and r[1].lower() not in items:
                os.makedirs(new_path)          
                return True, r[1]      
            else:
                printInfo = '폴더가 이미 존재합니다'           
                QMessageBox.warning(self.parent, 'Warning', printInfo) 
                return False, ''
        else:
            return False, ''
                                       

    def get_sub_folders(self, folder_path):
        # 하위 폴더 리스트 구하기
        sub_folders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
        return sub_folders
        
        
    def if_contain_json(self, path):
        # 폴더 안에 json이 있는지 없는지 확인, 
        # json이 있는 폴더는 카테고리에 보여줄 필요가 없음
        files = os.listdir(path)
        for f in files:
            if f.endswith('.json'):
                return True
        return False
        
        
    def get_category_len(self):
        get_combobox_list =  self.parent.findChildren(QComboBox)         

        num = 0
        for combobox in get_combobox_list:
            box_name =  combobox.objectName()
            match = re.search(r'(\d{2})', box_name)        
            box_num = int(match.group()) if match else None               
            if num < box_num:
                num = box_num
        
        if self.category_combobox.currentText() != 'HDRI':
            num += 1
            
        return num


#
# macro sub menu  ==============================================================
#                        


class SubWindow(QDialog):
    def __init__(self, parent=None, category=None):
        super(SubWindow, self).__init__(parent)
        self.initUI()

        self.name_label.setText(category)
                
                
    def initUI(self):
        self.setWindowTitle('New Category')
        self.setMinimumWidth(230)
        self.setMinimumHeight(130)        

        main_layout = QVBoxLayout(self)
        self.name_label = QLabel(self)
        main_layout.addWidget(self.name_label)
        self.name_lineEdit = QLineEdit(self)
        main_layout.addWidget(self.name_lineEdit)
        button_layout = QHBoxLayout()
        button_layout.setObjectName(u"horizontalLayout_2")
        horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        button_layout.addItem(horizontalSpacer)
        self.OK_Button = QPushButton(self)
        self.OK_Button.setText('OK')
        button_layout.addWidget(self.OK_Button)
        self.cancel_botton = QPushButton(self)
        self.cancel_botton.setText('Cancel')
        button_layout.addWidget(self.cancel_botton)
        main_layout.addLayout(button_layout)

        self.OK_Button.clicked.connect(self.onOKButtonClicked)
        self.cancel_botton.clicked.connect(self.onCancelButtonClicked)
        
        
    def onOKButtonClicked(self):
        self.accept()
        
        
    def onCancelButtonClicked(self):
        self.reject()
        
        
    def showModal(self):
        return super(SubWindow, self).exec_(), self.name_lineEdit.text()
        


