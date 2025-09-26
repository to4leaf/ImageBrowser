import os
import sys


def hdri_ext():
    IMAGE_EXT = ('.png', '.jpg', '.jpeg',  '.tif', '.tiff', '.exr', '.exr', '.hdr', '.raw')
    return IMAGE_EXT


def image_ext():
    IMAGE_EXT = ('.png', '.jpg', '.jpeg',  '.tif', '.tiff', '.exr') #'.raw' ## '.hdr', '.dpx'
    return IMAGE_EXT


def video_ext():
    VIDEO_EXT = ('.mp4', '.mov', '.gif') #'.avi', '.mkv'  ##'.ogv'
    return VIDEO_EXT


def get_ocio():
    OCIO = {
        'name': 'aces 1.0.3',
        'path': '/westworld/inhouse/tool/rez-packages/ocio_config/master/platform-linux/arch-x86_64/OpenColorIO-Configs/aces_1.0.3/config.ocio',
        'config': '1.0.3'}
    return OCIO


def get_prman_browser_path():
    path = '/storenext/user/lgt/joonsoo/test/prman_preset_browser/RenderManAssetLibrary'
    return path


def get_image_source_path():
    path = '/storenext/user/lgt/joonsoo/test/p_library_folder/LightSourceLibrary/WW'
    return path


def get_show_source_path():
    path = '/storenext/user/lgt/joonsoo/test/p_library_folder/LightSourceLibrary/Show'
    return path


def get_user_source_path():
    path = '/storenext/user/lgt/joonsoo/test/p_library_folder/LightSourceLibrary/User'
    return path


