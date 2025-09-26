# -*- coding: utf-8 -*-
import os
import sys
import cv2
import json
import re

import numpy as np
import PyOpenColorIO as OCIO

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


import browser_modules_init
reload(browser_modules_init)
import preview_widget_ui
reload(preview_widget_ui)


IMAGE_EXT = browser_modules_init.image_ext()
VIDEO_EXT = browser_modules_init.video_ext()

# OpenColorIO 설정 파일 경로 설정
OCIO_CONFIG = browser_modules_init.get_ocio()
os.environ['OCIO'] = OCIO_CONFIG['path']


class Widget():
    def __init__(self, all_swatch, sel_swatch):     
        #초기 설정
        self.all_swatch = all_swatch
        self.current_swatch = sel_swatch 
        self.preview_thread = None        
        self.first_image_item = None 
        
        # Load UI     
        self.ui = preview_widget_ui.Ui()  
        self.ui.on_close = self.clean_up    
        
        #초기 실행
        self.set_init_path()    
        self.ui.graphics_view.scene().clear()                     
        self.set_file_tree()
        self.change_graphic_view() # selectionChanged이 초기에 시작을 안해서 
        self.ui.preview_treewidget.selectionModel().selectionChanged.connect(self.change_graphic_view) 

        # Buttons
        self.ui.left_btn.clicked.connect(lambda: self.swap_swatch_items('left_btn'))      
        self.ui.right_btn.clicked.connect(lambda: self.swap_swatch_items('right_btn'))      
        

    def set_init_path(self):        
        # swatch에서 json 경로에 라이브러리 탐색
        json_path = self.current_swatch._asset.jsonFilePath()        
        # open prman json file        
        with open(json_path, 'r') as prman_json:
            self.prman_data = json.load(prman_json)

        self.preview_path = os.path.join(self.prman_data['lightSourcePath'], 'preview')           
        self.ui.main_label.setText(self.prman_data['name'])

        
    def swap_swatch_items(self, button):
        # 리스트 카테고리 순회       
        all_swatch_list = self.all_swatch
        current_index =  self.all_swatch.index(self.current_swatch)     
    
        add_index = 1
        if button == 'left_btn':
            add_index = -1

        new_index = (current_index + add_index) % len(all_swatch_list)        
        self.current_swatch = all_swatch_list[new_index]  
        
        # 재설정
        self.first_image_item = None        
        self.set_init_path()           
        self.ui.graphics_view.scene().clear()          
        self.set_file_tree() 


    def set_file_tree(self):    
        # QTreeWidget 초기화
        self.ui.preview_treewidget.clear()  # 기존 트리뷰 초기화

        # 루트 디렉토리 아이템 생성
        root_item = QTreeWidgetItem([os.path.basename(self.preview_path)])
        root_item.setData(0, Qt.UserRole, self.preview_path)
        self.ui.preview_treewidget.addTopLevelItem(root_item)

        # 폴더 트리 데이터를 수집하여 QTreeWidget에 추가
        self.populate_tree_widget(root_item, self.preview_path)
        
        if self.first_image_item:
            self.ui.preview_treewidget.setCurrentItem(self.first_image_item)

        # 첫 번째 항목을 확장
        self.ui.preview_treewidget.expandAll()


    def populate_tree_widget(self, parent_item, parent_path):
        sequences = {}
        pattern = re.compile(r"(.*?)(\d{4})(\.\w+)$")  # 4자리 숫자만 매칭

        try:
            for entry_name in os.listdir(parent_path):
                entry_path = os.path.join(parent_path, entry_name)
               
                if os.path.isdir(entry_path):
                    # 디렉토리인 경우
                    dir_item = QTreeWidgetItem(parent_item, [entry_name])
                    dir_item.setData(0, Qt.UserRole, entry_path)  # 전체 경로 저장
                    self.populate_tree_widget(dir_item, entry_path)
                else:
                    # 파일인 경우
                    match = pattern.match(entry_name)
                    if match and match.group(3).lower() in IMAGE_EXT:
                        base_name = match.group(1)  # "aa."
                        frame_number = int(match.group(2))  # "1001"
                        extension = match.group(3)  # ".exr"

                        key = (base_name, extension)
                        if key not in sequences:
                            sequences[key] = []
                        sequences[key].append(frame_number)
                    else:
                        # 일반 파일인 경우 바로 추가
                        file_item = QTreeWidgetItem(parent_item, [entry_name])
                        file_item.setData(0, Qt.UserRole, entry_path)

                        # 첫 번째 이미지를 선택하는 로직
                        check_path = file_item.data(0, Qt.UserRole).split('/')[-2]
                        if self.first_image_item is None and check_path == 'sample_image':
                            self.first_image_item = file_item

            # 시퀀스 항목들을 트리에 추가
            for (base_name, extension), frames in sequences.items():
                frames.sort()
                first_frame = frames[0]
                last_frame = frames[-1]
                padding = len(str(first_frame))
                sequence_name = "{}%0{}d{} ({}-{})".format(base_name, padding, extension, first_frame, last_frame)
                sequence_item = QTreeWidgetItem(parent_item, [sequence_name])
                sequence_item.setData(0, Qt.UserRole, os.path.join(parent_path, sequence_name))

        except:
            pass


    def change_graphic_view(self):             
        selected_items = self.ui.preview_treewidget.selectedItems()
        if selected_items:
            item = selected_items[0]
            file_path = item.data(0, Qt.UserRole)
            name = os.path.basename(file_path)
            ext = os.path.splitext(file_path)[-1]
            # set preview name
            self.ui.preview_name.setText(name)

            self.stop_preview_thread() #
            # 이미지 시퀀스 확인
            if '%0' in file_path and '(' in file_path and ')' in file_path:
                sequence_format = file_path
                self.load_graphic(sequence_format, types='image_sequence')
            else:
                # 기존 이미지, 비디오 처리 로직
                if ext.lower() in IMAGE_EXT:
                    self.ui.graphics_view.video_controls.hide() # 비디오 포맷이 아닌 경우 숨겨주기                                           
                    self.load_graphic(file_path, types='image')                          
                elif ext.lower() in VIDEO_EXT:
                    self.load_graphic(file_path, types='video')
                else:
                    self.ui.graphics_view.video_controls.hide() # 비디오 포맷이 아닌 경우 숨겨주기                                        
                    self.ui.graphics_view.display_image('', 'error_type')
                
            
    def load_graphic(self, path, types):     
        self.preview_thread = VideoThread(path, types)
        self.preview_thread.video_loaded.connect(self.update_graphic)
        self.preview_thread.progress_updated.connect(self.ui.graphics_view.video_controls.update_progress)
        self.ui.graphics_view.set_video_thread(self.preview_thread)

        # start
        self.preview_thread.start()

                                        
    def update_graphic(self, qt_image, types, width, height):
        if width > 5000 or height > 5000:
            self.ui.graphics_view.display_image('', 'error_size')                               
        else:
            self.ui.graphics_view.display_image(qt_image, types)

        
    def stop_preview_thread(self):
        if self.preview_thread:
            self.preview_thread.stop()
            self.preview_thread = None


    def clean_up(self):
        # ui에 closeEvent를 실행했을 경우    
        self.stop_preview_thread()
        
        
#
# VideoThread  ==============================================================
#


class VideoThread(QThread):
    video_loaded = pyqtSignal(QImage, str, int, int)
    progress_updated = pyqtSignal(int, int, str)

    def __init__(self, path, tpyes):
        super(VideoThread, self).__init__()
        self.path = path
        self.tpyes = tpyes
        self.init_ui()     


    def init_ui(self):
        self._lock = QMutex()                
        self._running = True
        self._paused = False
        self.current_frame = 0
        self.total_frame = 0
        self.fps = 0
        self.image_files = []
        
        
    def run(self):
        self._running = True
        if self.tpyes == 'image':
            self.load_image()
        elif self.tpyes == 'image_sequence':
            self.load_image_sequence()        
        else:
            self.load_video()


    def load_image(self):
        self._running = True
        if not self._running: # stop했을 때
            return
            
        image = set_image(self.path)         
        if image is None: # 이미지를 읽지 못할 때  
            print('Failed to load image')
            return

        qt_image, w, h = convert_cv_color(image)
        self.video_loaded.emit(qt_image, 'image' , w, h)    


    def load_image_sequence(self):
        self.image_files = self.image_file_list()
        self.total_frame = len(self.image_files)
        self.fps = 24  # 24 프레임으로 설정

        while self._running:
            if self.current_frame >= self.total_frame:
                self.current_frame = 0
                
            with QMutexLocker(self._lock):
                if self._paused:
                    continue
           
            qt_image, w, h = self.image_files[self.current_frame]
            if qt_image is not None:
                if self._running:
                    self.loop_images(qt_image, 'image_seq' , w, h)                
                    self.current_frame += 1

            # 이미지 로딩이 미리 완료되었으므로 msleep을 줄일 수 있음
            self.msleep(int(1000 / self.fps))  
            
            
    def load_video(self):
        self.cap = cv2.VideoCapture(self.path)
        if self.cap.isOpened():
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.total_frame = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.current_frame = 0
            frame_delay = int(round(self.fps, 0))            
            
            while self._running:      
                if self.current_frame >= self.total_frame:
                    self.current_frame = 0            
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    
                with QMutexLocker(self._lock):
                    if self._paused:
                        continue
            
                ret, frame = self.cap.read()
                if not ret or not self._running:
                    break
                    
                qt_image, w, h = convert_cv_color(frame)

                self.loop_images(qt_image, 'video' , w, h)
                self.current_frame += 1

                self.msleep(frame_delay)


    def image_file_list(self):         
        split_name = self.path.split(" (")[0]
        base_name, extension = os.path.splitext(split_name)
        frame_range = self.path.split(" (")[1].strip(")").split("-")
        start_frame = int(frame_range[0])
        end_frame = int(frame_range[1])        
        
        file_list = []
        for frame in range(start_frame, end_frame +1):
            file_name = split_name % frame
            image = set_image(file_name)
            
            if image is not None:
                qt_image, w, h = convert_cv_color(image)
                file_list.append((qt_image, w, h))
            else:
                file_list.append(None)  # 로딩 실패한 이미지에 대해 None 추가            

        return file_list
        
        
    def loop_images(self, qt_image, types , w, h):
        remaining_time = self.cal_remaining_time(self.current_frame, self.total_frame, self.fps)
        self.video_loaded.emit(qt_image, types , w, h)
        self.progress_updated.emit(self.current_frame, self.total_frame, remaining_time)
        
          
    def cal_remaining_time(self, current_frame, total_frame, fps):
        remaining_seconds = (total_frame - current_frame) / fps
        minutes = int(remaining_seconds // 60)
        seconds = int(remaining_seconds % 60)
        return '{:02}:{:02}'.format(minutes, seconds)


    def update_video(self, new_video_path):
        self._running = False
        self.wait()
        self.video_path = new_video_path
        self._running = True
        self.start()
        
    
    def video_play(self):
        if not self.isRunning():
            self.start()
        with QMutexLocker(self._lock):
            self._paused = False
            
            
    def video_pause(self):
        with QMutexLocker(self._lock):
            self._paused = True    
            
            
    def video_stop(self):
        if self.tpyes == 'image_sequence':
            self.move_to_first_frame_seq()
            with QMutexLocker(self._lock):
                self._paused = True                    
        else:
            with QMutexLocker(self._lock):
                self._running = False
                self._paused = True
                
            if self.isRunning():
                self.quit()
                self.wait()
                
            self.move_to_first_frame_video()        
            
            
    def move_to_first_frame_seq(self):
        # 이미지 시퀀스
        self.current_frame = 0
        if self.image_files:
            qt_image, w, h = self.image_files[0]
            if qt_image is not None:
                self.loop_images(qt_image, 'image_seq' , w, h)  

        self.video_pause()
        
        
    def move_to_first_frame_video(self):      
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.total_frame = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)              
        
        ret, frame = self.cap.read()
        if ret:         
            qt_image, w, h = convert_cv_color(frame)                
            self.current_frame = 0
            self.loop_images(qt_image, 'video' , w, h)

            
    def stop(self):
        self._running = False
        self.quit()
        self.wait()
  
  
        
#
# 이미지 관련 변환  ==============================================================
#


def set_image(image_path):
    if os.path.splitext(image_path)[-1] in ['.exr']:
     
        image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED | cv2.IMREAD_ANYDEPTH)

        # 부동 소수점 이미지 (0-1 범위) -> 8비트 이미지 (0-255 범위)
        if image.dtype == np.float32 or image.dtype == np.float64:
            image_8bit = np.clip(image * 255, 0, 255).astype(np.uint8)

        # 16비트 이미지 (0-65535 범위) -> 8비트 이미지 (0-255 범위)
        if image.dtype == np.uint16:
            image_8bit = (image / 256).astype(np.uint8)

        image = image_8bit
                
    else:
        image = cv2.imread(image_path)


    return image


def convert_cv_color(image):
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb_image.shape
    bytes_per_line = ch * w
    qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
    return qt_image, h, w
        
        
        

        
        
        
        
        
        
