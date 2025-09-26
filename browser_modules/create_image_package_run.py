# -*- coding: utf-8 -*-
import re
import os
import sys
import json
import shutil
import yaml
import subprocess

from pprint import pprint
from collections import OrderedDict
from functools import partial

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


import browser_modules_init
reload(browser_modules_init)
import create_image_package_ui as ui
reload(ui)
import create_image_package_convert_module as convert_module
reload(convert_module)
import create_image_package_json_module as json_config
reload(json_config)



class Widget():
    CMD_LIST = []
    OCIO = browser_modules_init.get_ocio()
    PRMAN_BROWSER_PATH = browser_modules_init.get_prman_browser_path()
    IMAGE_EXT = browser_modules_init.image_ext()
    
    def __init__(self):        
        self.cancel_flag = False
        self.cancel_status = None        
        self.final_category = None
        self.data_dict = {}               
        # Load UI     
        self.ui = ui.Ui()      
        # set
        self.init_setup()
        self.btn_triggers()


    def init_setup(self):
        # 초기 설정
        self.ui.author_edit.setText(os.environ['USER'])
        self.update_category('HDRI')        
        # progress thread
        self.progressTask = TaskThread()
        self.progressTask.TASK_FINISHED.connect(self._onFinished)
        self.progressTask.PROGRESS_UPDATED.connect(self._updateProgress)

        self.ui.category.browse_folder(self.ui.category.category_combobox)
        
    def btn_triggers(self):                       
        self.ui.image_tablewidget.tableEmpty.connect(self.set_frist_row_name)       
        self.ui.create_button.clicked.connect(self.create_button_clicked)
        self.ui.cancel_button.clicked.connect(self.cancel_button_clicked)        

        self.ui.category.change_categories.connect(self.update_category)                 

                
    def set_frist_row_name(self):
        # 카테고리 첫번째가 메인이름이지만 가독성을 위해 라벨로 보여주기 위함
        first_row_item = self.ui.image_tablewidget.item(0, 0)    
        if first_row_item == None:
            return            

        table_widget = self.ui.image_tablewidget                  
        total_count = table_widget.rowCount()   
        set_name = table_widget.item(0, 0).text()
        match = re.search(r'(\d{4})(?=D*$)', set_name)        
        num = str(match.group()) if match else None                
        seq_frame = []     
        # 시퀀스
        if total_count > 1 and num != None:                
            set_name = set_name.split(num)[0].rstrip('_.')
            end_frame = int(num) + total_count -1
            seq_frame = [num, str(end_frame)]

        self.data_dict['name'] = str(set_name)
        self.data_dict['frame'] = seq_frame          
        self.ui.name_edit.setText(set_name)
        
        
    def update_category(self, final_path):
        # set mode
        get_categoty = self.ui.category.category_combobox.currentText()             

        if get_categoty == 'HDRI':
            self.mode = 'HDRI'
        else:
            find_object = self.ui.findChild(QComboBox, 'store_combobox_01')             
            get_object = find_object.currentText()                 
            if get_object == 'Gobo':
                self.mode = 'Gobo'        
            elif get_object == 'IES':
                self.mode = 'IES'      
            else:
                self.mode = ''      
                
        # reload meta list
        self.ui.meta.reload_essential_meta(self.mode)
        self.final_category =  final_path
                
    def get_resolutuions(self):           
        mode = self.data_dict['mode']     
        
        if mode == 'IES':                       
            set_res = {}
        else:
            table_widget = self.ui.image_tablewidget                                          
            size = table_widget.item(0, 1).text()

            width = int(size.split('x')[0]) if size else None                 
            if width >= 15360:
                if  mode == 'HDRI':    
                    set_res = {'2k': '12.5%', '4k': '25%', '8k': '50%', '16k': '100%'}
                else:         
                    set_res = {'16k': '100%'}                                   
            elif width >= 7680:
                if  mode == 'HDRI':    
                    set_res = {'2k': '25%', '4k': '50%', '8k': '100%'}
                else:         
                    set_res = {'8k': '100%'}                    
            elif width >= 3840:
                if  mode == 'HDRI':    
                    set_res = {'2k': '50%', '4k': '100%'}
                else:         
                    set_res = {'4k': '100%'}                 
            else:
                set_res = {'2k': '100%'}

        self.data_dict['res_dict'] = set_res            
            
            
    def get_color_space(self):       
        mode = self.data_dict['mode']     
        set_color = []    
        if  mode == 'HDRI':        
            set_color = ['ACES', 'sRGB']
        elif mode == 'Gobo':
            set_color = ['linear']        

        self.data_dict['color_splace'] = set_color          


    def get_table_items(self):
        #접미사가 있으면 리스트 구하기
        image_table = self.ui.image_tablewidget        
        asset_name = image_table.item(0, 0).text()
        mode = self.data_dict['mode']        

        org_path_list = []
        suffix_list = []
        for row in range(0, image_table.rowCount()):
            name_item = image_table.item(row, 0).text()
            suffix = name_item.split(asset_name)[-1].replace('_', '')
            if mode == 'HDRI':
                suffix_list.append(str(suffix))

            org_path_list.append(str(image_table.item(row, 2).text()))            
          
        self.data_dict['org_list'] = org_path_list
        self.data_dict['suffix_list'] = suffix_list                        
      
                
    def get_ext(self):
        mode = self.data_dict['mode']     
            
        set_ext = ['exr', 'tex']
        if mode == 'IES':
            set_ext = ['ies']

        self.data_dict['ext_list'] = set_ext    
            
                        
    def get_size(self):
        size =  self.ui.image_tablewidget.item(0, 1).text()
        set_size = []
        if size:
            set_size = [int(i) for i in self.ui.image_tablewidget.item(0, 1).text().split('x')]
            self.data_dict['size'] = set_size    
            self.data_dict['width'] = str(set_size[0])
            self.data_dict['height'] = str(set_size[1])                                
        else:
            self.data_dict['size'] = ''    
            self.data_dict['width'] = ''
            self.data_dict['height'] = ''



    def get_category_list(self):
        split_item = self.final_category.split('/')
        clean_list = [str(item) for item in split_item]
        
        self.data_dict['category'] = clean_list    
        
                
    def check_table_items(self):                            
        mode = self.data_dict['mode']
        label_name = self.data_dict['name']
        table_widget = self.ui.image_tablewidget                          
        total_count = table_widget.rowCount()  
        
        first_row_size = table_widget.item(0, 1).text()        
        first_row_name = table_widget.item(0, 0).text()               

        issue, error, seq = 0, 0, 0      
        for row in range(0, total_count):    
            name_item = table_widget.item(row, 0)
            size_item = table_widget.item(row, 1)           
            if name_item == None or size_item == None:
                self.data_dict['issue_check'] = '아이템에 이름 또는 사이즈가 없습니다.'
                return 
                
            [table_widget.item(row, i).setForeground(QColor(150,150,150)) for i in range(0, 5)] # set gray                                

            # 이름 유효성 검사
            if mode == 'Gobo': #4자리로 해야 시퀀스 구분이 편할것같음
                if label_name not in name_item.text(): 
                    table_widget.item(row, 0).setForeground(QColor(255,165,0))    
                    issue += 1                       
                    seq += 1      
            elif mode == 'HDRI':                  
                if first_row_name not in name_item.text():
                    table_widget.item(row, 0).setForeground(QColor('red'))
                    error += 1                       
            elif mode == 'IES':           
                if total_count > 2 and row > 1:               
                    [table_widget.item(row, i).setForeground(QColor('red')) for i in range(0, 5)] # set red               
                    error += 1                                                                          
                else:
                    if table_widget.item(row, 3).text().lower() != '.ies' and row == 0:
                        table_widget.item(row, 3).setForeground(QColor(255,165,0))                      
                        issue += 1    

                    if table_widget.item(row, 3).text().lower() not in Widget.IMAGE_EXT and row == 1:
                        table_widget.item(row, 3).setForeground(QColor(255,165,0))                      
                        issue += 1                            

            # 이미지 사이즈가 다른지 체크
            if first_row_size != size_item.text() and mode != 'IES':
                table_widget.item(row, 1).setForeground(QColor('red'))
                error += 1                      

        # 정리                
        if error > 0 or issue > 0:
            self.data_dict['issue_check'] = '{0}개의 문제와 {1}개의 위험을 찾았습니다.\n\n'.format(error, issue)           


    def check_category_len(self):
        category_num = self.ui.category.get_category_len()
                
        if category_num < 3:
            self.data_dict['issue_check'] = 'Category가 너무 짧습니다.'                   


    def convert_prman_path(self):
        prman_path = Widget.PRMAN_BROWSER_PATH
        final_category = self.final_category
        
        final_category_split = final_category.split('/')
        fisrt_category = final_category_split[0]
        else_category = '/'.join(final_category_split[1:])
        
        if fisrt_category == 'LightFilter':
            fisrt_category = 'LightRigs'                
        elif fisrt_category == 'HDRI':
            fisrt_category = 'EnvironmentMaps'
            
        second_category = self.ui.category.path_category_combobox.currentText()
        
        convert_path = os.path.join(Widget.PRMAN_BROWSER_PATH, 
                                                fisrt_category, 
                                                second_category, 
                                                else_category)                                      
                
                
        self.data_dict['prman_path'] = str(os.path.join(convert_path, self.data_dict['name']+'.rma'))                                
        
        
    def convert_library_path(self):
        category_path = self.ui.category.path_category_combobox.currentData()
        add_path = self.final_category
        asset_name = self.data_dict['name']

        self.data_dict['library_path'] = str(os.path.join(category_path, add_path, asset_name))                   
               
                
    def set_data_dict(self):
        # data
        if self.ui.image_tablewidget.rowCount() == 0:
            self.data_dict['issue_check'] = '아이템이 존재하지 않습니다.'         
            return 
        #
        self.data_dict['mode'] = self.mode
        self.data_dict['dependencies_exr'] = ''
        self.data_dict['dependencies_tex'] = ''
        self.data_dict['format'] = str(self.ui.image_tablewidget.item(0, 3).text())
        self.data_dict['bit_depth'] = str(self.ui.image_tablewidget.item(0, 4).text())                            
        self.data_dict['channel'] = str(self.ui.image_tablewidget.item(0, 5).text())                                    
        self.data_dict['issue_check'] = ''                                                 
        # set data                    
        self.check_category_len()                   
        self.check_table_items() # table 아이템 네이밍 체크           
        self.convert_prman_path()
        self.convert_library_path()        
        self.get_table_items()         
        self.get_resolutuions()
        self.get_color_space()
        self.get_ext()
        self.get_size()
        self.get_category_list()
        
        
    def set_metadata(self):
        self.meta_dict = OrderedDict()   
        line_edits = self.ui.findChildren(QLineEdit)
        for edit in line_edits:
            if 'linename__' in edit.objectName() and edit.isVisible():
                edit_name =  edit.objectName().replace('linename__', 'lineedit__')                
                lineedit = self.ui.findChild(QLineEdit, edit_name).text()                          
                linename = edit.text() 
                
                if linename:
                    self.meta_dict[str(linename)] = str(lineedit)
                
            
    def create_button_clicked(self):
        # 변환에 필요한 데이터 만들기
        self.set_metadata()
        self.set_data_dict()        

        if self.data_dict['issue_check']:
            QMessageBox.warning(self.ui, 'Warning', self.data_dict['issue_check'])     
            return 
            
        # 이미 폴더가 존재하는지 따라, 현재는 덮는 방식만 지원
        if  os.path.isdir(self.data_dict['library_path']) or os.path.isdir(self.data_dict['prman_path']): 
            message =  '해당 폴더가 이미 존재합니다.\n덮어쓰겠습니까?'
            box_result = QMessageBox.warning(self.ui, 'Warning', message, QMessageBox.Ok | QMessageBox.Cancel)     
            if box_result == QMessageBox.Cancel:
                return
            elif box_result == QMessageBox.Ok:
                self.del_folder()           


        # 타입별로 cmd list 구하기
        cmd_list = []
        if self.data_dict['mode'] == 'HDRI':   
            single_path = self.ui.image_tablewidget.item(0, 2).text()              
            cmd_list = convert_module.make_hdri_cmd_list(self.data_dict, Widget.OCIO, single_path)
        elif self.data_dict['mode'] == 'Gobo':   
            cmd_list, data_dict = convert_module.make_gobo_cmd_list(self.data_dict)
            self.data_dict = data_dict
            if self.data_dict['frame']:                
                cmd_list = cmd_list + convert_module.make_mov(self.data_dict)
        elif self.data_dict['mode'] == 'IES':   
            cmd_list, data_dict = convert_module.make_ies_cmd_list(self.data_dict)
            self.data_dict = data_dict


        if cmd_list:
            # json 만들기
            json_config.MakeJson(self.data_dict, self.meta_dict, Widget.OCIO) 
            # TaskThread 실행       
            Widget.CMD_LIST = cmd_list                  
            self._onStart()          

       
    def cancel_button_clicked(self):
        if self.cancel_status:
            self.progressTask.stop()
            self.cancel_flag = True        
        else:        
            self.ui.reject()      

    
    def del_folder(self):
        if os.path.isdir(self.data_dict['library_path']):
            shutil.rmtree(self.data_dict['library_path'])
        if os.path.isdir(self.data_dict['prman_path']):
            shutil.rmtree(self.data_dict['prman_path'])      
                     
                     
    def _onStart(self):
        #start bar
        self.ui.create_button.setEnabled(False)
        self.progressTask.start()
        self.ui.progressbar.setRange(0, 100)


    def _onFinished(self):
        # gobo 시퀀스 제작시 tmp 파일 지우기
        gobo_seq_tmp_path = os.path.join(self.data_dict['library_path'], 'preview/sample_sequence/tmp')
        if os.path.isdir(gobo_seq_tmp_path):
            shutil.rmtree(gobo_seq_tmp_path)
        
        #message box        
        if self.cancel_flag:
            self.del_folder()
            QMessageBox.about(None, 'Cancelled..!!!', 'Cancelled!!!!')
            
        elif TaskThread.STATUS == 0:
            QMessageBox.about(None, 'Done..!!!', 'Created!!!!')
        else:
            QMessageBox.warning(None, 'Warning', 'Check plz. error messaage')
            
        # close
        self.ui.accept()
        
        
    def _updateProgress(self, value):
        self.cancel_status = True
        self.ui.progressbar.setValue(value)

                
    def showModal(self):
        return self.ui.exec_(), self.data_dict
        
      
#
# TaskThread  ==============================================================
#
               
        
class TaskThread(QtCore.QThread):
    TASK_FINISHED = pyqtSignal()
    PROGRESS_UPDATED = pyqtSignal(int)    
    STATUS = ''
    
    _stop_flag = False
    
    def run(self):         
        total_commands = len(Widget.CMD_LIST)        
        for index, command in enumerate(Widget.CMD_LIST):
            if self._stop_flag:
                break
            TaskThread.STATUS = os.system(command)   
            progress = int(((index + 1) / total_commands) * 100)
            self.PROGRESS_UPDATED.emit(progress)

        self.TASK_FINISHED.emit()  
        

    def stop(self):
        self._stop_flag = True
        




