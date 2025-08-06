
from functools import cached_property
from pathlib import Path

import h5py
import numpy as np
from detector import Detector

piranha_dict = {'piranha': 'c_piranha'}
apds_dict = {'full_area': 'full_area',
             'preproc': 'wfintegrate'}
fim0_dict = apds_dict 
fim1_dict = apds_dict 
lightstatus_dict = {'laser': 'laser',
                    'xray': 'xray'}
encoder_dict = {'mono': 'value'}
timestamp_dict = {'timestamp': 'timestamp'}
timing_dict = {'evtcodes': 'eventcodes',
               'timestamp': 'timestamp'}



class Singleshot():

    def __init__(self, ssgrp: h5py.Group):
        grp = ssgrp
        print(grp.keys())
        print(grp['det_crix_w8'].keys())
        self.piranha = Detector(grp, piranha_dict)
        self.apds = Detector(grp["det_crix_w8"], apds_dict)
        self.fim0 = Detector(grp["det_rix_fim0"], fim0_dict)
        self.fim1 = Detector(grp["det_rix_fim1"], fim1_dict)
        self.lightstatus = Detector(grp["lightStatus"], lightstatus_dict)
        self.mono = Detector(grp["mono_hrencoder"], encoder_dict)
        # maybe define this differently self.scaninfo = Detector(grp["scan"], fim1_dict) # this depends on what sort of scan it is... how to load this best
        self.timing = Detector(grp["timing"], fim1_dict)



    '''

    def __init__(self, intgrp: h5py.Group):
        print('initialising Integrating')
        grp = intgrp
        self.andor_dir = Detector(grp["andor_dir"], andor_dir_dict)
        self.andor_vls = Detector(grp["andor_vls"], andor_vls_dict)
        self.axis_svls = Detector(grp["axis_svls"], axis_svls_dict)
            
            '''