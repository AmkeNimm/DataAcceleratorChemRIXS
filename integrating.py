
from functools import cached_property
from pathlib import Path

import h5py
import numpy as np
import yaml
from detector import Detector

andor_dir_dict = {
    'count': 'count',
    'full_area': 'full_area',
    'eventcodes': 'timing_sum_eventcodes',
    'apds': 'det_crix_w8_sum_full_area',
    'fim_0': 'det_rix_fim0_sum_full_area',
    'fim_1': 'det_rix_fim1_sum_full_area',
    'mono_encoder': 'mono_hrencoder_sum_value',
    'piranha': 'c_piranha_sum_full_area'}
andor_vls_dict = andor_dir_dict # assuming both detectors have the same keys

axis_svls_dict = andor_dir_dict # assuming both detectors have the same keys

detectors = {'andor_dir': andor_dir_dict,
                'andor_vls': andor_vls_dict,
                'axis_svls': axis_svls_dict,
                }

class Integrating():

    '''
    Class for accessing all data from the integrating detector

    This is also the place where you can define which variables are loaded from the h5 files
    and how they are called.
    '''

    def __init__(self, intgrp: h5py.Group):
        if 'andor_dir' in intgrp.keys():
            AndorDir = type('AndorDir', (Detector,), {})
            self.andor_dir = AndorDir(intgrp['andor_dir'], detectors['andor_dir'])       
        if 'andor_vls' in intgrp.keys():
            AndorVLS = type('AndorVLS', (Detector,), {})
            self.andor_vls = AndorVLS(intgrp['andor_vls'], detectors['andor_vls'])
        if 'axis_svls' in intgrp.keys():
            AxisSVLS = type('AxisSVLS', (Detector,), {}) 
            self.axis_svls = AxisSVLS(intgrp['axis_svls'], detectors['axis_svls'])


