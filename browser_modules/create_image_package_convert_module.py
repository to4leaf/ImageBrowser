# -*- coding: utf-8 -*-
import re
import os
import sys
import yaml
import shutil

from pprint import pprint
from collections import OrderedDict


def get_yaml_config():
    path = os.path.dirname(__file__)
    name = 'create_image_package_convert_config.yaml'
    file_path = os.path.join(path, name)

    with open(file_path, 'r') as yaml_file:
        data = yaml.safe_load(yaml_file)

    return  data

YAML = get_yaml_config()


def make_hdri_cmd_list(data_dict, ocio, single_path):
    ocio_path = ocio.get('path')
    cmd_list = []

    #렌더맨 프리뷰 이미지
    prman_preview = os.path.join(convert_directory(data_dict['prman_path'], ''), 'asset_100.png')        
    prman_preview_cmd = get_cmd_oiio(prman_preview, single_path, 'linear', 'sRGB', 'resize', '125x125')           
    cmd_list.append(prman_preview_cmd)

    # 리스트 만들기
    for index, input_path in enumerate(data_dict['org_list']):    
        library_path = data_dict['library_path']
        input_basename =  os.path.basename(input_path)
        input_name, ext = os.path.splitext(input_basename)
        preview_1k = str((0.5 ** len(data_dict['res_dict']) * 100)) + '%'                           

        # 프리뷰용 리스트 담기             
        prview_path = os.path.join(convert_directory(library_path, 'preview/sample_image'),
                                                    input_basename.replace(ext, '.png'))                 
        preview_cmd = get_cmd_oiio(prview_path, input_path, 'linear', 'sRGB', 'resample', preview_1k, ocio_path)           
        cmd_list.append(preview_cmd)         

        #원본      
        org_path = os.path.join(convert_directory(library_path, 'org/r0'),
                                            input_basename.replace(ext, '.exr'))                                
        org_cmd = get_cmd_oiio(org_path, input_path, 'default', 'default', 'resample', '100%')           
        cmd_list.append(org_cmd)                     

        for color in data_dict['color_splace']:                 
            for res_key, res_value in data_dict['res_dict'].items():                    
                # convert color name
                color_from = 'linear'
                color_to = convert_ocio_color_name(color)
                # ext 리스트 담기  
                ext_path = os.path.join(convert_directory(library_path, os.path.join(color, 'exr', res_key)),
                                                    input_basename.replace(ext, '.exr'))                                                  
                list_cmd = get_cmd_oiio(ext_path, input_path, color_from, color_to, 'resample', res_value, ocio_path)          
                cmd_list.append(list_cmd)                
                # tex 리스트 담기                               
                tex_path = os.path.join(convert_directory(library_path, os.path.join(color, 'tex', res_key)),
                                                    input_basename.replace(ext, '.tex'))                    
                tex_cmd = get_cmd_tex(tex_path, ext_path)       
                cmd_list.append(tex_cmd)       
                
                #
                target_resolution = '2k' if len(data_dict['res_dict']) <= 1 else '4k'
                if index == 0 and res_key == target_resolution and color == 'ACES':
                    data_dict['dependencies_exr'] = org_path
                    data_dict['dependencies_tex'] = tex_path

    return cmd_list


def make_gobo_cmd_list(data_dict):
    total_len = len(data_dict['org_list'])
    cmd_list = []
    for index, path in enumerate(data_dict['org_list']):
        library_path = data_dict['library_path']    
        preview_1k = str((0.5 ** len(data_dict['res_dict']) * 100)) + '%'     
    
        input_basename =  os.path.basename(path)
        input_name, ext = os.path.splitext(input_basename)

        
        #원본                
        org_path = os.path.join(convert_directory(library_path, 'org/r0'),
                                            input_basename.replace(ext, '.exr'))
        org_cmd = get_cmd_oiio(org_path, path, 'default', 'default', 'resample', '100%')           
        cmd_list.append(org_cmd)        

        tex_path = os.path.join(convert_directory(library_path,  'org/tex'),
                                            input_basename.replace(ext, '.tex'))
        tex_cmd = get_cmd_tex(tex_path, org_path)       
        cmd_list.append(tex_cmd)              
        
        if  index == 0:
            # 프리뷰용 리스트 담기              
            prview_path = os.path.join(convert_directory(library_path, 'preview/sample_image'),
                                                        input_basename.replace(ext, '.png'))
            preview_cmd = get_cmd_oiio(prview_path, path, 'linear', 'sRGB', 'resample', preview_1k)           
            cmd_list.append(preview_cmd)                          
            # 렌더맨
            prman_preview = os.path.join(convert_directory(data_dict['prman_path'], ''), 'asset_100.png')        
            prman_preview_cmd = get_cmd_oiio(prman_preview, path, 'linear', 'sRGB', 'resize', '125x125')           
            cmd_list.append(prman_preview_cmd)            
  
            # set dict
            data_dict['dependencies_exr'] = org_path
            data_dict['dependencies_tex'] = tex_path            


        if total_len > 1: 
            # 프리뷰용 시퀀스 담기              
            prview_seq_path = os.path.join(convert_directory(library_path, 'preview/sample_sequence/tmp'),
                                                                input_basename.replace(ext, '.exr'))
            preview_seq_cmd = get_cmd_oiio(prview_seq_path, path, 'linear', 'sRGB', 'resample', preview_1k)           
            cmd_list.append(preview_seq_cmd)           

            if  index == 0: #%4d에 맞게 dict 수정하기                                                          
                data_dict['dependencies_exr'] = convert_name_fomatting(org_path)
                data_dict['dependencies_tex'] = convert_name_fomatting(tex_path)                 
                
    return cmd_list, data_dict
    
    
def make_ies_cmd_list(data_dict):   
    library_path = data_dict['library_path']    

    cmd_list = []
    for input_path in data_dict['org_list']:
        input_dirname = os.path.dirname(input_path)
        input_basename =  os.path.basename(input_path)
        name, ext = os.path.splitext(input_basename)
        if ext.lower() == '.ies':
            dst_path = os.path.join(convert_directory(library_path, 'org/r0'),
                                                input_basename.replace(ext, '.ies'))                                                           
            
            shutil.copy2(input_path, dst_path)            
            data_dict['dependencies_exr'] = dst_path
            
        else:
            # 프리뷰용 리스트 담기             
            prview_path = os.path.join(convert_directory(library_path, 'preview/sample_image'),
                                                        input_basename.replace(ext, '.png'))                       
            preview_cmd = get_cmd_oiio(prview_path, input_path, 'linear', 'sRGB', 'resample', '100%')           
            cmd_list.append(preview_cmd)             
            
            # 렌더맨
            prman_preview = os.path.join(convert_directory(data_dict['prman_path'], ''), 'asset_100.png')        
            prman_preview_cmd = get_cmd_oiio(prman_preview, input_path, 'linear', 'sRGB', 'resize', '125x125')           
            cmd_list.append(prman_preview_cmd)                        
            
    return cmd_list, data_dict


def make_mov(data_dict):
    # package_run에서 실행
    get_dependencies_exr = data_dict['dependencies_exr']
    path_replace =  get_dependencies_exr.replace('org/r0', 'preview/sample_sequence/tmp')

    
    get_start_frame = data_dict['frame'][0]

    dst_path = os.path.join(data_dict['library_path'],
                                        'preview/sample_sequence', 
                                        data_dict['name']+'.mov')
    
    get_mov_cmd = ffmpeg_cmd(path_replace, dst_path, get_start_frame)
    return [get_mov_cmd]
    

#
#   ==============================================================
#  

    
def convert_name_fomatting(path):
    dirname =  os.path.dirname(path)
    basename =  os.path.basename(path)
    name, ext = os.path.splitext(basename)       
    
    match = re.search(r'(\d{4})(?=D*$)', name)
    num = str(match.group()) if match else None
    convert_name =  basename.replace(num, '%4d')
    
    return  os.path.join(dirname, convert_name)

    
def convert_directory(path, add_path):
    convert_path = os.path.join(path, add_path)
    
    if not os.path.exists(convert_path):
        os.makedirs(convert_path)             
        
    return convert_path
                            
    
def get_cmd_oiio(ext_path, input_path, color_from, color_to, res_func, res_value, ocio_path=None):
    ext = os.path.splitext(ext_path)[-1][1:]
    command = YAML['oiioSetting']['command']
    args = YAML['oiioSetting']['args']['default']
    if ext.lower() == 'png':
        args = YAML['oiioSetting']['args']['png']

    arg_cmd = ['echo create ------ %s ; '%(ext_path)]
    arg_cmd.append(command)
    for arg in args:
        arg_cmd.append(arg.format(input_path = input_path,
                                                    ocio_path = ocio_path,
                                                    color_from = color_from,
                                                    color_to = color_to,
                                                    res_func = res_func,
                                                    res_value = res_value,
                                                    ext_path = ext_path))

    return  ' '.join(arg_cmd)


def get_cmd_tex(tex_path, ext_path):    
    command = YAML['texSetting']['command']
    args = YAML['texSetting']['args']['default']
    version = YAML['texSetting']['version']

    arg_cmd = ['echo create ------ %s ; '%(tex_path)]    
    arg_cmd.append(command.format(version = version))
    for arg in args:
        arg_cmd.append(arg)

    arg_cmd.append(ext_path)   
    arg_cmd.append(tex_path)       

    return ' '.join(arg_cmd)
            
    
def ffmpeg_cmd(input_path, out_path, start_num):
    command = YAML['ffmpegSetting']['command']
    args = YAML['ffmpegSetting']['args']['default']

    arg_cmd = ['echo create ------ %s ; '%(out_path)]
    arg_cmd.append(command)
    for arg in args:
        arg_cmd.append(arg.format(input_path = input_path,
                                                    start_num = str(start_num),
                                                    out_path = out_path))
                            
    return  ' '.join(arg_cmd)


def convert_ocio_color_name(color):
    # 컬러 스페이스를 oiio config에 맞게 이름 변환
    convert_color_list = YAML['convertColorspace']
    
    for key, value in convert_color_list.items():
        if color == key:
            color = '"{}"'.format(value)

    return color








    
    
