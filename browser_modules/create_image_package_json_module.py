# -*- coding: utf-8 -*-
import re
import os
import sys
import json
import yaml

from pprint import pprint
from datetime import datetime
from collections import OrderedDict


class MakeJson():
    def __init__(self, data_dict, meta_dict, ocio):     
        # dict data 가져오기
        self.data_dict = data_dict
        self.meta_dict = meta_dict
        self.ocio = ocio
        self.convert_yaml = self.get_yaml_config('create_image_package_convert_config')        
        self.json_yaml = self.get_yaml_config('create_image_package_json_config')
        #
        self.mode = self.data_dict['mode']        
        self.library_path = self.data_dict['library_path']        
        self.prman_path = self.data_dict['prman_path']                

        # update self.json_yaml
        self.set_asset()
        self.set_metadata()        
        # update metadata
        self.update_metadata(self.json_yaml['metadata'])           
        self.add_manual_metadata(self.json_yaml['metadata'])

        self.update_yaml(self.json_yaml['ocio'])     
        self.update_yaml(self.json_yaml['compatibility'])         
        self.update_yaml(self.json_yaml['libraryJson'])        
        self.update_yaml(self.json_yaml['prmanJson'])           

        # save json
        self.save_json()

            
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
        
        
    def set_asset(self):
        if self.mode == 'HDRI':
            self.json_yaml['prmanJson']['RenderManAsset']['asset'] = {'envMap' : self.json_yaml['envMap']}
        else:
            self.json_yaml['prmanJson']['RenderManAsset']['asset'] = {'nodeGraph' : self.json_yaml['nodeGraph']} 
        

    def set_metadata(self):
        meta = self.json_yaml['metadata'] = OrderedDict()
        meta.update(self.json_yaml['meta']['default']['auto'])        

        if self.mode == 'HDRI':
            meta.update(self.json_yaml['meta']['image']['auto'])
            meta.update(self.json_yaml['meta']['hdri']['auto'])                                           
        elif self.mode == 'Gobo':
            meta.update(self.json_yaml['meta']['image']['auto'])
            meta.update(self.json_yaml['meta']['gobo']['auto'])             
        elif self.mode == 'IES':                              
            pass 



    def update_metadata(self, yaml):
        now = datetime.now()             
               
        for key, value in yaml.items():
            if isinstance(value, list):
                #print value
                if value[0] == 'data_dict':    
                    if value[1] in ['frame']:
                        if self.data_dict.get(value[1]) == []:
                            yaml[key] = 'Single'                            
                        else:
                            yaml[key] = '-'.join(self.data_dict.get(value[1]))                        
                    elif value[1] in ['res_dict']:
                        yaml[key] = ', '.join(self.data_dict.get(value[1]).keys())
                    elif value[1] == 'size':
                        get_size = self.data_dict.get(value[1])
                        yaml[key] = str(get_size[0]) + ' x ' + str(get_size[1])                    
                    elif value[1] in ['color_splace', 'suffix_list', 'category', 'ext_list']:
                        yaml[key] = ', '.join(self.data_dict.get(value[1]))       
                    else:
                        yaml[key] = self.data_dict.get(value[1])
                elif key == 'author':
                    yaml[key] = os.environ.get('USER', 'unknown')               
                elif key == 'created':
                    yaml[key] = now.strftime('%Y-%m-%d %H:%M:%S')
                # 나머지는 그냥 추가      
                else:
                    yaml[key] = value
            else:    
                yaml[key] = value

        
    def add_manual_metadata(self, yaml):
        for key, value in self.meta_dict.items():
            yaml[key] = value
            

    def update_yaml(self, yaml):
        for key, value in yaml.items():
            if isinstance(value, dict):
                self.update_yaml(value)
            elif isinstance(value, list):
                if value:    
                    # data_dict에 대한 정보 추가
                    if value[0] == 'data_dict':           
                        if value[1] in ['res_dict']:
                            yaml[key] = self.data_dict.get(value[1]).keys()
                        else:
                            yaml[key] = self.data_dict.get(value[1])                          
                    # ocio에 대한 정보 추가                    
                    elif  value[0] == 'ocio':
                        yaml[key] = self.ocio.get(value[1])
                    # yaml에 있는거 추가
                    elif value[0] == 'self':
                        yaml[key] = self.json_yaml.get(value[1])
                    # 나머지는 그냥 추가                
                    else:
                        yaml[key] = value
                else:
                    yaml[key] = value
            else:
                yaml[key] = value                    
            
        
    def save_json(self):
        # library_path
        if not os.path.exists(self.library_path):
            os.makedirs(self.library_path)
            
        with open(os.path.join(self.library_path, 'data.json'), 'w') as lib_json_file:
            json.dump(self.json_yaml['libraryJson'], lib_json_file, ensure_ascii=False, indent=4, encoding='utf-8')  
                  
        # prman_path
        if not os.path.exists(self.prman_path):
            os.makedirs(self.prman_path)       
            
        with open(os.path.join(self.prman_path, 'asset.json'), 'w') as prm_json_file:
            json.dump(self.json_yaml['prmanJson'], prm_json_file, ensure_ascii=False, indent=4, encoding='utf-8')  
        

    
    
