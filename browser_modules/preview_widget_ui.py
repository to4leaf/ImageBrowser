# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
 
   

class Ui(QWidget):
    def __init__(self):
        super(Ui, self).__init__()        
        # init setting.
        self.init_ui()
        self.set_layout()


    def init_ui(self): 
        # 초기 설정    
        self.setObjectName('preview_widget')        
        self.setWindowTitle('WW PrmanPresetBrowser Preview')   
        self.setMinimumSize(750, 450)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)


    def set_layout(self):   
        # Create the main layout    
        layout = QVBoxLayout()       
        top_layout = QHBoxLayout()                
        self.left_btn = QPushButton(self)
        self.left_btn.setStyleSheet('font-size: 12pt;')           
        self.left_btn.setText('◀')        
        self.left_btn.setMaximumSize(QtCore.QSize(35, 16777215))
        top_layout.addWidget(self.left_btn)                
        left_spacer = QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        top_layout.addItem(left_spacer)                
        self.main_label = QLabel(self)
        self.main_label.setStyleSheet('font-size: 12pt; font-weight: bold;')      
        self.main_label.setAlignment(QtCore.Qt.AlignCenter)
        self.main_label.setText('Main Name')
        top_layout.addWidget(self.main_label)                
        right_spacer = QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        top_layout.addItem(right_spacer)                   
        self.right_btn = QPushButton(self)  
        self.right_btn.setStyleSheet('font-size: 12pt;')           
        self.right_btn.setText('▶')        
        self.right_btn.setMaximumSize(QtCore.QSize(35, 16777215))
        top_layout.addWidget(self.right_btn)          
        layout.addLayout(top_layout)                           
        preview_layout = QHBoxLayout()             
        self.preview_treewidget = MyTreeview(self)                   
        preview_layout.addWidget(self.preview_treewidget)        
        graphics_layout = QVBoxLayout()
        self.graphics_view = ImageView(self) #QGraphicsView
        graphics_layout.addWidget(self.graphics_view)                 
        self.preview_name = QLabel(self)
        self.preview_name.setText('Preview Name')            
        self.preview_name.setStyleSheet('font-size: 9pt')         
        self.preview_name.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_name.setMaximumSize(QtCore.QSize(16777215, 22))
        graphics_layout.addWidget(self.preview_name)                                         
        preview_layout.addLayout(graphics_layout)        
        preview_layout.setStretch(0,1)        
        preview_layout.setStretch(1,3)                  
        layout.addLayout(preview_layout)

        # Set the layout for the panel
        self.setLayout(layout)        
                
                
    def closeEvent(self, event):
        if hasattr(self, 'on_close'):
            self.on_close()
        event.accept()
                

#
# MyTreeview  ==============================================================
#


class MyTreeview(QTreeWidget):
    def __init__(self, parent=None):
        super(MyTreeview, self).__init__(parent)        
        self.init_ui()

    def init_ui(self):
        # 초기 설정
        self.setStyleSheet('font-size: 9pt')            
        self.setMaximumSize(QtCore.QSize(450, 16777215))                                  
        self.setSortingEnabled(True)
        self.sortByColumn(2, Qt.AscendingOrder)       
        self.setHeaderLabels(["Folder Structure"])  # 헤더 설정
        
    def keyPressEvent(self, event):
        # 알파벳 및 숫자 키를 무시합니다.
        if event.key() in range(QtCore.Qt.Key_A, QtCore.Qt.Key_Z+1) or \
           event.key() in range(QtCore.Qt.Key_0, QtCore.Qt.Key_9+1):
            return  
        else:
            super(MyTreeview, self).keyPressEvent(event) 


#
# 이미지 보여주는 위젯  ==============================================================
#
                
class ImageView(QGraphicsView):
    #
    MAX_SCALE_FACTOR = 8.0      
    CONTROL_WIDTH = 200
    CONTROL_HEIGHT = 50        
    CONTROL_MARGIN_BOTTOM = 40
    ZOOM_IN_FACTOR = 1.25
    ZOOM_OUT_FACTOR = 1 / ZOOM_IN_FACTOR        
                
    def __init__(self, parent=None):
        super(ImageView, self).__init__(parent)
        self.init_ui()                    
        self.video_controls = VideoControls(self)
        self.video_controls.hide()
       
                
    def init_ui(self):
        # 초기 설정
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setFocusPolicy(Qt.StrongFocus)    
 
        self.scale_factor = 1.0
        self.current_type = None        
        

    def display_image(self, qt_image, types):
        self.current_type = types
        self.scene().clear()        
        
        if 'error' in types and 'type' in types: # 포맷이 이상한 경우
            text = 'No Image' 
            self.set_text(text)      
        elif 'error' in types and 'size' in types: # 사이즈가 큰 경우        
            text = 'Size is large.\nOnly 4k or less'           
            self.set_text(text)        
        else: # 그외 이미지 그리기
            self.set_image(qt_image)
            
            
    def set_text(self, text):       
        # 텍스트 부분
        text_item = QGraphicsTextItem(text)
        font = QFont('Arial', 12, QFont.StyleItalic)
        text_item.setFont(font)
        text_item.setDefaultTextColor(QColor(255, 255, 255, 50))  # 텍스트 색상 설정
        self.scene().addItem(text_item)        
        # 사이즈 고정
        self.setSceneRect(QRectF(1024, 0, 512, 0))                
        text_item.setPos(self.sceneRect().center() - text_item.boundingRect().center())        
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        # resizeEvent 무시하기 위해서
        self.scale_factor = 0.9
            
            
    def set_image(self, image):
        # 이미지 그리기
        self.pixmap = QPixmap.fromImage(image)
        self.pixmap_item = QGraphicsPixmapItem(self.pixmap)
        self.scene().addItem(self.pixmap_item)
        self.setSceneRect(QRectF(self.pixmap.rect()))
        # ImageView 사이즈에 맞춤
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        # 기본 값
        self.scale_factor = 1.0               
            

    def wheelEvent(self, event):
        if self.current_type == 'image':
            self.handle_zoom(event)


    def handle_zoom(self, event):
        # 확대할지 축소할지 결정
        requested_factor = self.ZOOM_IN_FACTOR if event.angleDelta().y() > 0 else self.ZOOM_OUT_FACTOR
        # 실제 적용할 스케일 팩터 계산
        new_scale_factor = self.scale_factor * requested_factor

        # 최대 및 최소 스케일 팩터에 대한 경계 조건 검사
        if new_scale_factor > self.MAX_SCALE_FACTOR:
            factor = self.MAX_SCALE_FACTOR / self.scale_factor  # 최대 경계에 맞춤
        elif new_scale_factor < 1:
            factor = 1 / self.scale_factor  # 최소 경계에 맞춤
        else:
            factor = requested_factor

        # 확대/축소 적용
        self.scale(factor, factor)
        self.scale_factor *= factor

    
    def resizeEvent(self, event):
        # 이미지가 정사이즈 일때, 화면 크기를 조절 했을때 따라간다.
        if self.scale_factor == 1.0:
            self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        # 비디오 컨트롤러 중앙에 유지                    
        if self.video_controls.isVisible():            
            self.position_video_controls()            
        super(ImageView, self).resizeEvent(event)


    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F:
            self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
            self.scale_factor = 1.0  
        super(ImageView, self).keyPressEvent(event)   
        
        
    def mousePressEvent(self, event):
        if self.current_type == 'video' or self.current_type == 'image_seq':
            self.toggle_video_contrls()
        super(ImageView, self).mousePressEvent(event)
        
        
    def toggle_video_contrls(self):
        if self.video_controls.isVisible():
            self.video_controls.hide()
        else:        
            self.position_video_controls()
            self.video_controls.show()


    def position_video_controls(self):
        parent_rect = self.rect()        
        x = (parent_rect.width() - self.CONTROL_WIDTH) / 2
        y = parent_rect.height() - self.CONTROL_HEIGHT - 40        
        self.video_controls.setGeometry(x, y, self.CONTROL_WIDTH, self.CONTROL_HEIGHT)
            

    def set_video_thread(self, thread):
        # VideoControls과 VideoThread 연결해주는 통로
        self.video_controls.set_video_thread(thread)


#
# 비디오 컨트롤러  ==============================================================
#

class VideoControls(QWidget):
    def __init__(self, parent=None, video_thread=None):
        super(VideoControls, self).__init__(parent)
        #
        self.video_thread = video_thread                      
        self.init_ui()
        self.set_layout()        
        self.connect_signals()
           

    def init_ui(self):
        # 초기 설정
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)  

        
    def set_layout(self):
        layout = QVBoxLayout()
        
        top_layout = QHBoxLayout()
        self.progress_slider = QSlider(Qt.Horizontal, self)
        self.progress_slider.setRange(0, 100)
        top_layout.addWidget(self.progress_slider)
        self.time_label = QLabel('00:00', self)
        top_layout.addWidget(self.time_label)        
        
        bot_layout = QHBoxLayout()
        self.play_btn = QPushButton('재생', self)
        bot_layout.addWidget(self.play_btn)        
        self.pause_btn = QPushButton('일시정지', self)
        bot_layout.addWidget(self.pause_btn)        
        self.stop_btn = QPushButton('정지', self)
        bot_layout.addWidget(self.stop_btn)
        
        layout.addLayout(top_layout)        
        layout.addLayout(bot_layout)            
        self.setLayout(layout)    
    

    def connect_signals(self):
        self.play_btn.clicked.connect(self.play_video)
        self.pause_btn.clicked.connect(self.pause_video)
        self.stop_btn.clicked.connect(self.stop_video)     
    
        
    def set_video_thread(self, video_thread):
        # VideoThread에 연결하기 위함
        # VideoControls에서 ImageView에 까지 보냄
        self.video_thread = video_thread   
        
        
    def play_video(self):
        # VideoThread에 신호 전달
        if self.video_thread:
            self.video_thread.video_play()
    
    
    def pause_video(self):
        # VideoThread에 신호 전달    
        if self.video_thread:
            self.video_thread.video_pause() 


    def stop_video(self):      
        # VideoThread에 신호 전달      
        if self.video_thread:
            self.video_thread.video_stop()


    def mousePressEvent(self, event):
        event.accept()            


    def update_progress(self, current_frame, total_frame, remaining_time):
        #VideoThread에에서 progress_updated 신호를 받아 계속 업데이트
        self.progress_slider.setMaximum(total_frame)
        self.progress_slider.setValue(current_frame)
        self.time_label.setText(remaining_time)
        









                
