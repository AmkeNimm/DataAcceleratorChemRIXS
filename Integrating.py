
from functools import cached_property
from pathlib import Path

import h5py
import numpy as np
import yaml
from loadDat import *

class Integrating():

    '''
    Class for accessing all data related to 
    '''

    def __init__(self, intgrp: h5py.Group):
        print('initialising Integrating')
        grp = intgrp
        try:
            self.andor_dir = Detector(grp["andor_dir"], ['crix_w8_sum_ptrigCount','det_crix_w8_sum_full_area'])
        except:
            print(f'Andor_dir not in data')
        try:
            self.andor_vls = Detector(grp["andor_vls"], ['crix_w8_sum_ptrigCount','det_crix_w8_sum_full_area'])
        except:
            print(f'Andor_VLS not in data')
        try:
            self.axis_svls = Detector(grp["axis_svls"], ['crix_w8_sum_ptrigCount','det_crix_w8_sum_full_area'])
        except:
            print(f'Andor_dir not in data')

