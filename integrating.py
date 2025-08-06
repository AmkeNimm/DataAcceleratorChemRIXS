
from functools import cached_property
from pathlib import Path

import h5py
import numpy as np
import yaml
from detector import Detector

andor_dir_dict = {
    'count': 'count',
    'full_area': 'full_area',
    'timing_sum_eventcodes': 'eventcodes',
    'det_crix_w8_sum_full_area': 'APDs',
    'det_rix_fim0_sum_full_area': 'fim_0',
    'det_rix_fim1_sum_full_area': 'fim_1',
    'mono_hrencoder_sum_value': 'mono_encoder',
    'c_piranha_sum_full_area': 'piranha'}

andor_vls_dict = andor_dir_dict # assuming both detectors have the same keys

axis_svls_dict = andor_dir_dict # assuming both detectors have the same keys

class Integrating():

    '''
    Class for accessing all data from the integrating detector

    This is also the place where you can define which variables are loaded from the h5 files
    and how they are called.
    '''

    def __init__(self, intgrp: h5py.Group):
        print('initialising Integrating')
        grp = intgrp
        self.andor_dir = Detector(grp["andor_dir"], andor_dir_dict)
        self.andor_vls = Detector(grp["andor_vls"], andor_vls_dict)
        self.axis_svls = Detector(grp["axis_svls"], axis_svls_dict)
            


