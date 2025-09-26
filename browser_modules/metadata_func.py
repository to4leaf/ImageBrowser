# -*- coding: utf-8 -*-
import os
import json
import shutil
import subprocess
import yaml

from pprint import pprint
from collections import OrderedDict

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class UpdateMeta(QDialog):
    def __init__(self, cursor_pos, sel_swatch):
        super(UpdateMeta, self).__init__()
        self.initUI()
        self.move(cursor_pos) 
        #get datas
        self.swatch = sel_swatch                 
        self.get_json()    
        self.set_metadata()
        
        self.OK_Button.clicked.connect(self.onOKButtonClicked)
        self.cancel_botton.clicked.connect(self.onCancelButtonClicked)


    def initUI(self):
        self.setWindowTitle('Update Metadata')
        self.resize(750, 200)

        layout = QVBoxLayout()
        grid_layout = QGridLayout()
        self.name_label = QLabel(self)
        self.name_label.setText('Asset Name')
        grid_layout.addWidget(self.name_label, 0, 0, 1, 1)
        self.name_edit = QLabel(self)
        self.name_edit.setText('-9999')
        grid_layout.addWidget(self.name_edit, 0, 1, 1, 1)

        self.meta_label = QLabel()
        self.meta_label.setText('Metadata')
        grid_layout.addWidget(self.meta_label, 1, 0, 1, 1)
        self.meta_layout = QVBoxLayout()
        grid_layout.addLayout(self.meta_layout, 1, 1, 1, 1)
        self.meta = CreateMeta(self)              
        self.button_layout = QHBoxLayout()
        horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.button_layout.addItem(horizontalSpacer)
        self.OK_Button = QPushButton(self)
        self.OK_Button.setText('OK')
        self.button_layout.addWidget(self.OK_Button)
        self.cancel_botton = QPushButton(self)
        self.cancel_botton.setText('Cancel')
        self.button_layout.addWidget(self.cancel_botton)
        grid_layout.addLayout(self.button_layout, 2, 1, 1, 1)

        layout.addLayout(grid_layout)
        self.setLayout(layout)


    def get_json(self):
        self.prman_json_path = self.swatch._asset.jsonFilePath()     
       
        # open prman json file        
        with open(self.prman_json_path, 'r') as p_json:
            self.prman_json = json.load(p_json)                        

        # open library json file     
        self.library_json_path = os.path.join(str(self.prman_json['lightSourcePath']), 'data.json')
        with open(self.library_json_path, 'r') as l_json:
            self.library_json = json.load(l_json, object_pairs_hook=OrderedDict) 
               
        self.name_edit.setText(self.library_json['name'])


    def update_meta(self):
        self.new_meta_dict = OrderedDict()
        self.new_meta_dict.update(self.fixed_meta)        
        line_edits = self.findChildren(QLineEdit)
        for edit in line_edits:
            if 'linename__' in edit.objectName() and edit.isVisible():
                edit_name =  edit.objectName().replace('linename__', 'lineedit__')                
                lineedit = self.findChild(QLineEdit, edit_name).text()                          
                linename = edit.text() 
                
                if linename:
                    self.new_meta_dict[str(linename)] = str(lineedit)


    def set_metadata(self):         
        self.meta.hide_all()
        self.fixed_meta = self.meta.set_metadata(self.library_json['metadata'])
        
        
    def save_json(self):
        self.library_json['metadata'] = self.new_meta_dict
        try: 
            self.prman_json['RenderManAsset']['asset']['envMap']['metadata'] = self.new_meta_dict
        except:
            self.prman_json['RenderManAsset']['asset']['nodeGraph']['metadata'] = self.new_meta_dict  

        # library
        with open(os.path.join(self.library_json_path), 'w') as lib_json_file:
            json.dump(self.library_json, lib_json_file, ensure_ascii=False, indent=4, encoding='utf-8')  
            
        # prman
        with open(os.path.join(self.prman_json_path), 'w') as prm_json_file:
            json.dump(self.prman_json, prm_json_file, ensure_ascii=False, indent=4, encoding='utf-8')          
                   
           
    def onOKButtonClicked(self):
        self.update_meta()
        self.save_json()
        self.accept()


    def onCancelButtonClicked(self):
        self.reject()


    def showModal(self):
        result = self.exec_()


#
# CreateMeta  ==============================================================
#


class CreateMeta(QObject):
    def __init__(self, parent):
        super(CreateMeta, self).__init__(parent)
        self.json_yaml = self.get_yaml_config('create_image_package_json_config')        

        self.attr_list = self.get_manual_meta_list('default')       
        self.hdri_list = self.get_manual_meta_list('hdri')
        self.gobo_list = self.get_manual_meta_list('gobo')
        self.ies_list = self.get_manual_meta_list('ies')
        self.fixed_list = self.get_fixed_meta_list()

        self.parent = parent
        self.initUI()


    def initUI(self):
        self.scroll_contect = QWidget()
        self.scroll_layout = QVBoxLayout()
        # 기존 자동등록되는 레이아웃
        self.essential_layout = QVBoxLayout()
        for attr in self.hdri_list + self.gobo_list + self.ies_list + self.attr_list:
            self.create_essential_list(attr)
        self.scroll_layout.addLayout(self.essential_layout, 1)
        self.scroll_contect.setLayout(self.scroll_layout)

        self.parent.meta_layout.addWidget(self.scroll_contect)

        
    def get_yaml_config(self, name):
        # OrderedLoader 사용하여 YAML 파일 로드 시 순서 유지
        class OrderedLoader(yaml.SafeLoader):
            pass

        def construct_mapping(loader, node):
            loader.flatten_mapping(node)
            return OrderedDict(loader.construct_pairs(node))

        OrderedLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            construct_mapping
        )

        path = os.path.dirname(__file__)
        file_path = os.path.join(path, name + '.yaml')

        with open(file_path, 'r') as yaml_file:
            data = yaml.load(yaml_file, Loader=OrderedLoader)  # OrderedLoader로 YAML 순서 유지

        return data

        
    def get_manual_meta_list(self, name):
        keys = []

        if self.json_yaml['meta'][name]['manual']:
            keys = self.json_yaml['meta'][name]['manual'].keys()            
        
        return keys
        
        
    def get_fixed_meta_list(self):
        keys = []
        keys += self.json_yaml['meta']['default']['auto'].keys()
        keys += self.json_yaml['meta']['image']['auto'].keys()
        keys += self.json_yaml['meta']['hdri']['auto'].keys()
        keys += self.json_yaml['meta']['gobo']['auto'].keys()
        
        return keys
        
    
    def create_essential_list(self, attr_name):
        essential_layout = QHBoxLayout()

        essential_name = QLineEdit(self.parent)
        essential_name.setText(attr_name)
        essential_name.setObjectName('linename__{}'.format(attr_name))
        essential_name.setReadOnly(True)
        essential_name.installEventFilter(self)        
        essential_edit = QLineEdit(self.parent)
        essential_edit.setObjectName('lineedit__{}'.format(attr_name))
        essential_edit.setReadOnly(True)
        essential_edit.installEventFilter(self)
                
        essential_layout.addWidget(essential_name, 1)
        essential_layout.addWidget(essential_edit, 3)
        self.essential_layout.addLayout(essential_layout)
        
        
    # essential_name만 이벤트 필터 설치함
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonDblClick:
            if isinstance(obj, QLineEdit):
                point_x = self.parent.pos().x() + self.parent.rect().width()//2 - 100
                point_y = self.parent.pos().y() + self.parent.rect().height()//2 - 100            
                adjusted_pos = QtCore.QPoint(point_x, point_y)             

                # 더블 클릭 시 RadioSelectionDialog 열기
                obj_name =  str(obj.objectName().split('__')[-1])          
                dialog = RadioSelectionDialog(obj_name, adjusted_pos, self.parent)                
                if dialog.exec_() == QDialog.Accepted:
                    selected_item = dialog.get_selected_items()

                    edit_name = 'lineedit__{}'.format(obj_name)
                    edit_attr = self.parent.findChild(QLineEdit, edit_name)                    
                    edit_attr.setText(selected_item)          
                                               
                return True  # 이벤트를 처리했음을 알리기 위해 True 반환
        return super(CreateMeta, self).eventFilter(obj, event)

        
    def reload_essential_meta(self, mode):    
        if mode:
            if mode == 'HDRI':
                # show
                for show_attr in self.hdri_list:
                    self.show_lineedit(show_attr)
                # hide
                for hide_attr in self.gobo_list + self.ies_list:
                    self.hide_lineedit(hide_attr)
                    
            elif mode == 'Gobo':
                # show
                for show_attr in self.gobo_list:
                    self.show_lineedit(show_attr)
                # hide
                for hide_attr in self.hdri_list + self.ies_list:
                    self.hide_lineedit(hide_attr)
                    
            elif mode == 'IES':
                # show
                for show_attr in self.ies_list:
                    self.show_lineedit(show_attr)
                # hide
                for hide_attr in self.hdri_list + self.gobo_list:
                    self.hide_lineedit(hide_attr)


    def hide_all(self):
        for hide_attr in self.hdri_list + self.gobo_list + self.ies_list:
            self.hide_lineedit(hide_attr)


    def hide_lineedit(self, attr):
        get_name_attr = self.parent.findChild(QLineEdit, 'linename__{}'.format(attr))        
        get_edit_attr = self.parent.findChild(QLineEdit, 'lineedit__{}'.format(attr))
        
        if get_name_attr is not None:
            get_name_attr.setVisible(False)
        if get_edit_attr is not None:
            get_edit_attr.setText('')
            get_edit_attr.setVisible(False)
            

    def show_lineedit(self, attr):
        get_name_attr = self.parent.findChild(QLineEdit, 'linename__{}'.format(attr))        
        get_edit_attr = self.parent.findChild(QLineEdit, 'lineedit__{}'.format(attr))
        
        if get_name_attr is not None:
            get_name_attr.setVisible(True)
        if get_edit_attr is not None:
            get_edit_attr.setVisible(True)
   
            
    def set_metadata(self, meta_dict):
        fixed_data = OrderedDict()
        for key, value in meta_dict.items():
            get_name_attr = self.parent.findChild(QLineEdit, 'linename__{}'.format(key))        
            get_edit_attr = self.parent.findChild(QLineEdit, 'lineedit__{}'.format(key))
            
            if get_name_attr:   
                get_name_attr.setVisible(True)            
                get_edit_attr.setVisible(True)            
                get_edit_attr.setText(value)
            else:
                if key not in self.fixed_list:
                    self.add_lineedit(key, value)
                else:
                    fixed_data[str(key)] = str(value)
                    
        return fixed_data
        
        
#
# RadioSelectionDialog  ==============================================================
#


class RadioSelectionDialog(QDialog):
    def __init__(self, obj_name, cursor_pos, parent=None):
        super(RadioSelectionDialog, self).__init__()
        self.setWindowTitle('Select Sample Items')
        self.setGeometry(100, 100, 300, 100)
        self.move(cursor_pos)        
        # 딕셔너리의 key를 라벨로, value를 체크박스로 표시
        self.checkboxes = {}      
        self.lineedit_counter = 1        
        # 선택할 체크박스 항목들
        self.items = self.get_item_list(obj_name)
        #
        self.init_ui()
        
        self.add_button.clicked.connect(self.add_lineedit)
        self.remove_button.clicked.connect(self.remove_lineedit)

    def init_ui(self):
        layout = QVBoxLayout()                           
        self.set_checkbox_items(layout)
        self.set_add_items(layout)

        # 확인 버튼
        self.ok_button = QPushButton('OK', self)
        self.ok_button.clicked.connect(self.accept)
        layout.addWidget(self.ok_button)

        self.setLayout(layout)


    def set_checkbox_items(self, layout):
        for key, values in  self.items.items():
            # key를 라벨로 추가
            label = QLabel(self)
            label.setText(key)
            label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)              
            layout.addWidget(label)

            # 그리드 레이아웃을 생성하여 체크박스를 배치
            grid_layout = QGridLayout()

            # 항목을 가로로 3줄씩 배치
            self.checkboxes[key] = []
            for index, item in enumerate(values):
                checkbox = QCheckBox(item, self)
                self.checkboxes[key].append(checkbox)

                row = index // 3
                col = index % 3
                grid_layout.addWidget(checkbox, row, col)

            layout.addLayout(grid_layout)
            

    def set_add_items(self, layout):
        # 버튼 레이아웃
        meta_btn_layout = QHBoxLayout()
        self.add_button = QPushButton(self)
        self.add_button.setText('+')
        meta_btn_layout.addWidget(self.add_button)
        self.remove_button = QPushButton(self)
        self.remove_button.setText('-')
        meta_btn_layout.addWidget(self.remove_button)
        horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        meta_btn_layout.addItem(horizontalSpacer)
        layout.addLayout(meta_btn_layout)        
        #추가 메타데이터 레이아웃
        self.add_meta_layout = QVBoxLayout()
        layout.addLayout(self.add_meta_layout)        
                
 
    def add_lineedit(self):
        line_layout = QHBoxLayout()
        line_name = QLineEdit(self)
        line_name.setObjectName('addname__{}'.format(self.lineedit_counter))
        line_layout.addWidget(line_name, )

        self.lineedit_counter += 1
        self.add_meta_layout.addLayout(line_layout)

        self.layout_size_update('add')
        

    def remove_lineedit(self):
        if self.add_meta_layout.count() > 0:  # Add/Remove 버튼 제외
            last_layout = self.add_meta_layout.itemAt(self.add_meta_layout.count() - 1)
            if last_layout:
                for i in reversed(range(last_layout.layout().count())):
                    widget = last_layout.layout().itemAt(i).widget()
                    if widget:
                        widget.deleteLater()
                last_layout.layout().deleteLater()
                
            self.layout_size_update('remove')
            
        
    def layout_size_update(self, status):
        if status == 'add':
            self.resize(self.width(), self.height() + 30)
        else:                        
            self.resize(self.width(), self.height() - 30)     
                    
        
    def get_selected_items(self):
        # 선택된 항목들을 리스트로 반환
        selected_items = []
        for checkboxes in self.checkboxes.values():
            for checkbox in checkboxes:
                if checkbox.isChecked():
                    selected_items.append(checkbox.text())
                    
        line_edits = self.findChildren(QLineEdit)
        for edit in line_edits:
            if edit.text() and 'addname__' in edit.objectName():
                selected_items.append(edit.text())
                                        
        if len(selected_items) == 0:
            return ''
        if len(selected_items) == 1:
            return selected_items[0]            
        else:    
            return ', '.join(selected_items)


    def get_item_list(self, obj_name):
        path = os.path.dirname(__file__)
        file_path = os.path.join(path, 'metadata_sample_list.yaml')

        with open(file_path, 'r') as yaml_file:
            data = yaml.safe_load(yaml_file)

        return  data[obj_name]





