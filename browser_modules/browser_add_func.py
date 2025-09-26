# -*- coding: utf-8 -*-
import os
import json
import shutil
import subprocess

from pprint import pprint
from collections import OrderedDict

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


def delete_all_path(cursor_pos, swatch):   
    # QMessageBox 인스턴스 생성
    msg_box = QMessageBox()
    msg_box.setWindowTitle('Delete Files')
    msg_box.setText('모든 파일이 다 지워집니다.\n확인 하셨습니까?')
    msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg_box.setIcon(QMessageBox.Question)
    msg_box.move(cursor_pos)
    # 메시지 박스 표시 및 사용자 응답 받기
    reply = msg_box.exec_()

    # 사용자의 응답 확인 
    if reply == QMessageBox.Yes: 
        # swatch에서 json 경로에 라이브러리 탐색
        json_path = swatch._asset.jsonFilePath()        
        # open prman json file        
        with open(json_path, 'r') as s_json:
            json_data = json.load(s_json)
            
        library_path =  json_data['lightSourcePath']
        prman_path =  json_data['PrmanBrowserPath']

        if os.path.isdir(library_path):
            shutil.rmtree(library_path)
        if os.path.isdir(prman_path):
            shutil.rmtree(prman_path)
        return
    else:
        return
        
        
def open_folder(swatch, name):
    # swatch에서 json 경로에 라이브러리 탐색
    json_path = swatch._asset.jsonFilePath()        
    # open prman json file        
    with open(json_path, 'r') as s_json:
        json_data = json.load(s_json)
        
    if name == 'prman':
        path =  json_data['PrmanBrowserPath']     
    elif name == 'library':
        path =  json_data['lightSourcePath']             

    if os.path.isdir(path):
        subprocess.Popen(['gio', 'open', path])  


#
# RenameSwatch  ==============================================================
#


class RenameSwatch(QDialog):
    def __init__(self, cursor_pos, swatch):
        super(RenameSwatch, self).__init__()
        self.initUI()
        self.move(cursor_pos)          
        self.swatch = swatch  

        self.OK_Button.clicked.connect(self.onOKButtonClicked)
        self.cancel_botton.clicked.connect(self.onCancelButtonClicked)
  
                
    def initUI(self):
        self.setWindowTitle('Rename Swatch Item')
        self.setMinimumWidth(100)
        self.setMinimumHeight(130)        

        main_layout = QVBoxLayout(self)
        line_layout = QHBoxLayout()
        self.name_label = QLineEdit(self)
        line_layout.addWidget(self.name_label)
        main_layout.addLayout(line_layout)
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


    def get_data(self):
        self.prman_json_path = self.swatch._asset.jsonFilePath()     
       
        # open prman json file        
        with open(self.prman_json_path, 'r') as p_json:
            self.prman_json = json.load(p_json, object_pairs_hook=OrderedDict)  

        # open library json file     
        self.library_json_path = os.path.join(str(self.prman_json['lightSourcePath']), 'data.json')
        with open(self.library_json_path, 'r') as l_json:
            self.library_json = json.load(l_json, object_pairs_hook=OrderedDict) 
        
        get_prman_name = self.prman_json['RenderManAsset']['label']
        get_library_name = self.library_json['name']
        
        if get_prman_name == get_library_name:
            self.get_name = get_library_name
            self.name_label.setText(get_library_name)
            return True

        else:
            return None


    def convert_prman_json(self, old_name, new_name):
        old_path = self.prman_json['PrmanBrowserPath'] 
            
        self.prman_json['name'] = new_name
        self.prman_json['PrmanBrowserPath'] = self.prman_json['PrmanBrowserPath'].replace(old_name, new_name) 
        self.prman_json['lightSourcePath'] = self.prman_json['lightSourcePath'].replace(old_name, new_name)        
        self.prman_json['RenderManAsset']['label'] = new_name
        self.prman_json['RenderManAsset']['storage']['key'] = new_name        
        self.prman_json['RenderManAsset']['storage']['path'] = self.prman_json['RenderManAsset']['storage']['path'].replace(old_name, new_name)             
        
        with open(self.prman_json_path, 'w') as p_w_json:
            json.dump(self.prman_json, p_w_json, ensure_ascii=False, indent=4, encoding='utf-8')              
    
        os.rename(old_path, self.prman_json['PrmanBrowserPath'])        
        
        
    def convert_library_json(self, old_name, new_name):
        old_path = self.library_json['lightSourcePath'] 
    
        self.library_json['name'] = new_name  
        self.library_json['PrmanBrowserPath'] = self.library_json['PrmanBrowserPath'].replace(old_name, new_name) 
        self.library_json['lightSourcePath'] = self.library_json['lightSourcePath'].replace(old_name, new_name)        
        self.library_json['asset']['dependencies']['imageExt'] = self.library_json['asset']['dependencies']['imageExt'].replace(old_name, new_name) 
        self.library_json['asset']['dependencies']['imageTex'] = self.library_json['asset']['dependencies']['imageTex'].replace(old_name, new_name)        
        
        with open(self.library_json_path, 'w') as l_w_json: 
            json.dump(self.library_json, l_w_json, ensure_ascii=False, indent=4, encoding='utf-8')  
            
        os.rename(old_path, self.library_json['lightSourcePath'])        


    def rename_files_in_directory(self, root_dir, old_name, new_name):
        # os.walk()를 사용하여 하위 폴더까지 재귀적으로 탐색
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for filename in filenames:
                if old_name in filename:
                    # 이전 파일 경로
                    old_file_path = os.path.join(dirpath, filename)
                   
                    # 새로운 파일 경로
                    convert_name = filename.replace(old_name, new_name)
                    new_file_path = os.path.join(dirpath, convert_name)
                   
                    # 파일 이름 변경
                    os.rename(old_file_path, new_file_path)


    def onOKButtonClicked(self):
        old_name = self.prman_json['name']
        new_name = self.name_label.text()
        
        self.convert_prman_json(old_name, new_name)
        self.convert_library_json(old_name, new_name)
        
        source_path = self.prman_json['lightSourcePath']  
        self.rename_files_in_directory(source_path, old_name, new_name)
        self.accept()
        
        
    def onCancelButtonClicked(self):
        self.reject()
        
        
    def showModal(self):       
        status = self.get_data()             
        if status:
            result = self.exec_()         
            return result, self.name_label.text()
        else:
            printInfo = '라이브러리랑 렌더맨 브라우저랑\n이름이 같지 않습니다.'
            QMessageBox.warning(self, 'Warning', printInfo)                
            return None, None
        
        
        
        
        
        
        
        
