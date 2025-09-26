import os
import sys



os.environ["LD_LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH"] + ":/westworld/inhouse/tool/rez-packages/opencv/3.4.0/platform-linux/arch-x86_64/lib"
sys.path.append('/westworld/inhouse/tool/rez-packages/opencv/3.4.0/platform-linux/arch-x86_64/lib/python2.7/site-packages')
sys.path.append('/westworld/inhouse/tool/rez-packages/numpy/1.16.3/platform-linux/arch-x86_64/lib64/python2.7/site-packages')

os.environ["LD_LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH"] + ":/westworld/inhouse/tool/rez-packages/ocio/1.0.9/platform-linux/arch-x86_64/lib"
sys.path.append('/westworld/inhouse/tool/rez-packages/ocio/1.0.9/platform-linux/arch-x86_64/lib/python2.7/site-packages')


sys.path.append("/westworld/inhouse/dept_pipeline/rez-packages/lib/PyYAML/3.10/python")
