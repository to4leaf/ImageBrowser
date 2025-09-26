# -*- coding: utf-8 -*-
import os
import re
import cv2
import numpy as np

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import metadata_func
reload(metadata_func)
import cetegory_func
reload(cetegory_func)

class Ui(QDialog):
    UiPos = pyqtSignal(QPoint)

    def __init__(self):
        super(Ui, self).__init__()        
        # init setting.
        self.init_ui()
        self.set_layout()


    def init_ui(self):
        # 초기 설정    
        self.setObjectName('create_image_package')        
        self.setWindowTitle('Create Image Package')   
        self.setMinimumSize(750, 400)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        

    def set_layout(self):   
        # Create the main layout    
        layout = QVBoxLayout()               
        grid_layout = QGridLayout()            
        self.name_label = QLabel(self)
        self.name_label.setText('Asset Name')        
        grid_layout.addWidget(self.name_label, 0, 0, 1, 1)
        self.name_edit = QLineEdit(self)    
        self.name_edit.setReadOnly(True)            
        grid_layout.addWidget(self.name_edit, 0, 1, 1, 1)                
        self.author_label = QLabel(self)
        self.author_label.setText('Author')
        grid_layout.addWidget(self.author_label, 1, 0, 1, 1)                
        self.author_edit = QLineEdit(self)
        self.author_edit.setReadOnly(True)                 
        grid_layout.addWidget(self.author_edit, 1, 1, 1, 1)          
        self.category_label = QLabel(self)
        self.category_label.setText('Category')
        grid_layout.addWidget(self.category_label, 2, 0, 1, 1)    
        self.new_category_layout = QHBoxLayout()      
        grid_layout.addLayout(self.new_category_layout, 2, 1, 1, 1)                 
        # category
        self.category = cetegory_func.CreateCategory(self)        
        self.meta_label = QLabel()
        self.meta_label.setText('Metadata')                         
        grid_layout.addWidget(self.meta_label, 3, 0, 1, 1)                                 
        self.meta_layout = QVBoxLayout()                 
        grid_layout.addLayout(self.meta_layout, 3, 1, 1, 1)
        # meta
        self.meta = metadata_func.CreateMeta(self)
        table_layout = QVBoxLayout()
        self.image_label = QLabel(self)
        self.image_label.setText('Images')
        table_layout.addWidget(self.image_label)
        self.image_tablewidget = MyTableWidget(self)     
        table_layout.addWidget(self.image_tablewidget)            
        button_layout = QHBoxLayout()
        self.progressbar = QProgressBar(self)
        button_layout.addWidget(self.progressbar)        
        self.create_button = QPushButton(self)
        self.create_button.setText('Create')        
        button_layout.addWidget(self.create_button)
        self.cancel_button = QPushButton(self)
        self.cancel_button.setText('Cancel')        
        button_layout.addWidget(self.cancel_button)    
        layout.addLayout(grid_layout)        
        layout.addLayout(table_layout)    
        layout.addLayout(button_layout)                                     
        # Set the layout for the panel
        self.setLayout(layout)            

    
    def moveEvent(self, event):
        super(Ui, self).moveEvent(event)
        self.UiPos.emit(self.pos())

        
#
# MyTableWidget  ==============================================================
#
       

class MyTableWidget(QTableWidget):
    tableEmpty = pyqtSignal()

    def __init__(self, parent=None):
        super(MyTableWidget, self).__init__(parent)
        self.init_ui()          
        self.setMinimumSize(750, 250)
        
    def init_ui(self):
        # 초기 설정
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)        
        self.setAcceptDrops(True)                
        self.setDragEnabled(True)        
        self.setColumnCount(6)        
        self.setHorizontalHeaderItem(0, QTableWidgetItem('Name'))
        self.setHorizontalHeaderItem(1, QTableWidgetItem('Size'))         
        self.setHorizontalHeaderItem(2, QTableWidgetItem('Path')) 
        self.setHorizontalHeaderItem(3, QTableWidgetItem('Format')) 
        self.setHorizontalHeaderItem(4, QTableWidgetItem('BitDepth'))          
        self.setHorizontalHeaderItem(5, QTableWidgetItem('Channel'))                         
        self.setSelectionBehavior(QTableWidget.SelectRows)        
        self.setDragDropMode(QTableWidget.InternalMove)
        self.cellChanged.connect(self.update_items)

        
    def resizeEvent(self, event):
        total_width = self.viewport().width()
        column0_width = total_width * 0.25
        column1_width = total_width * 0.15
        column2_width = total_width * 0.3
        column3_width = total_width * 0.1        
        column4_width = total_width * 0.1        
        column5_width = total_width * 0.1                
                
        self.setColumnWidth(0, column0_width)
        self.setColumnWidth(1, column1_width) 
        self.setColumnWidth(2, column2_width)         
        self.setColumnWidth(3, column3_width)         
        self.setColumnWidth(4, column4_width)                         
        self.setColumnWidth(5, column5_width)                         

        super(MyTableWidget, self).resizeEvent(event)
        

    def startDrag(self, supportedActions):
        drag = QDrag(self)
        selected_row = self.currentRow()
        item = self.item(selected_row, 0)
        mime_data = QMimeData()
        mime_data.setText(item.text())
        drag.setMimeData(mime_data)
        drag.exec_(Qt.MoveAction)
                
        
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls or event.source() == self:
            event.accept()                
        else:
            event.ignore()
    
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls or event.source() == self:
            event.accept()                              
        else:
            event.ignore()    
        
        
    def dropEvent(self, event):
        if event.source() == self:
            event.accept()
            self.swap_rows(self.currentRow(), self.rowAt(event.pos().y()))                
        elif event.mimeData().hasUrls:
            event.accept()        
            row_count = self.rowCount()
            self.add_file(event.mimeData().urls())
        else:
            event.ignore()
            
        
    def swap_rows(self, source_row, target_row):
        if source_row != target_row and target_row != -1:
            for column in range(self.columnCount()):
                source_item = self.takeItem(source_row, column)
                target_item = self.takeItem(target_row, column)
                self.setItem(source_row, column, target_item)
                self.setItem(target_row, column, source_item)
            
    
    def add_file(self, urls):
        existing_paths = [self.item(row, 2).text() for row in range(self.rowCount())]
        
        for url in urls:
            file_path = url.toLocalFile()                
            file_name, file_ext = os.path.splitext(os.path.basename(file_path))
            file_size, image_format, bit_depth, channel = self.get_image_info(file_path)


            if file_path not in existing_paths:                             
                row_position = self.rowCount()
                self.insertRow(row_position)
                items = [                    
                    QTableWidgetItem(file_name),
                    QTableWidgetItem(file_size),
                    QTableWidgetItem(file_path),
                    QTableWidgetItem(file_ext),
                    QTableWidgetItem(bit_depth),
                    QTableWidgetItem(channel)                    
                ]

                # 열 설정
                for item in items:
                    item.setTextAlignment(Qt.AlignCenter)  

                # 행 설정                  
                for col, item in enumerate(items):
                    self.setItem(row_position, col, item)
                    set_item = self.item(row_position, col)                    
                    set_item.setForeground(QColor(150,150,150)) 
                    if col != 0:
                        set_item.setFlags(set_item.flags() & ~Qt.ItemIsEditable)            

            
    def get_image_info(self, path):
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is not None:
            image_format = path.split('.')[-1]
            bit_depth = img.dtype.itemsize * 8

            if len(img.shape) == 2:
                height, width = img.shape[:2]            
                channel = 'Gray'
            if len(img.shape) == 3:
                height, width, check = img.shape
                if check == 3:                
                    channel = 'RGB'   
                elif check == 4:                
                    channel = 'RGBA'   
            
            return str(width) + 'x' + str(height), image_format, str(bit_depth), channel
        else:
            return None, None, None, None
     

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.delete_selected_rows()
        else:
            super(MyTableWidget, self).keyPressEvent(event)


    def delete_selected_rows(self):
        selected_rows = set(index.row() for index in self.selectedIndexes())
        for row in sorted(selected_rows, reverse=True):
            self.removeRow(row)
            self.update_items()


    def update_items(self):
        self.update_row_boldness()
        self.tableEmpty.emit() # self.name_label 이름 바꿔주기 위함
     

    def update_row_boldness(self):
        font = self.font().toString().split(',')[0]
        normal_font = QFont(font, 8)
        bold_font = QFont(font, 8, QFont.Bold)

        for row in range(0, self.rowCount()):
            for col in range(self.columnCount()): 
                item = self.item(row, col)
                if item == None:
                    return     
                                    
                if row == 0:
                    item.setFont(bold_font)                      
                else:
                    item.setFont(normal_font)                                      


        
        
        
