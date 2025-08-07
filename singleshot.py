
from functools import cached_property
from pathlib import Path

import h5py
import numpy as np
from detector import Detector

piranha_dict = {'full_area': 'full_area'}
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

detectors = {'c_piranha': piranha_dict,
             'det_crix_w8': apds_dict,
             'det_rix_fim0': fim0_dict,
             'det_rix_fim1': fim1_dict,
             'lightStatus': lightstatus_dict,
             'mono_hrencoder': encoder_dict,
             'timing': timing_dict,
            }



class Singleshot():
    '''
    Class that is called by the small data class to load data from the single shot detectors.

    This class loads data through the Detector class as cached property -
    That way the data is only loaded once it is actually called. This makes it much faster to perform
    small tasks where simple metadata is required, rather than reading in the whole
    header.

    In this file the detectors to be loaded and the respective keys are being defind.

    Anything that is read in is stored in memory so the second access is much faster.
    However, the memory can be released simply by deleting the attribute (it can be
    accessed again, and the data will be re-read).


    Parameters:
    -----------
    ssgrp: h5py.Group
        group containing the single shot data defined in the small data class

    Notes:
    ------
    Detector and key names may need to be updated if small data structure changes


    '''
    def __init__(self, ssgrp: h5py.Group):
        
        grp = ssgrp
        if 'c_piranha' in ssgrp.keys():
            Piranha = type('Piranha',(Detector,),{})
            self.piranha = Piranha(grp['c_piranha'], detectors['c_piranha'])
        if 'det_crix_w8' in ssgrp.keys():
            Apds = type('Apds',(Detector,), {})
            self.apds = Apds(grp['det_crix_w8'], detectors['det_crix_w8'])
        if 'det_rix_fim0' in ssgrp.keys():
            Fim0 = type('Fim0',(Detector,), {})
            self.fim0 = Fim0(grp['det_rix_fim0'], detectors['det_rix_fim0'])
        if 'det_rix_fim1' in ssgrp.keys():
            Fim1 = type('Fim1',(Detector,),{})
            self.fim1 = Fim1(grp['det_rix_fim1'], detectors['det_rix_fim1'])
        if 'lightStatus' in ssgrp.keys():
            Lightstatus = type('Lightstatus',(Detector,),{})
            self.lightstatus = Lightstatus(grp['lightStatus'], detectors['lightStatus'])
        if 'mono_hrencoder' in ssgrp.keys():
            Mono = type('Mono', (Detector,), {})
            self.mono = Mono(grp['mono_hrencoder'], detectors['mono_hrencoder'])
        # maybe define this differently self.scaninfo = Detector(grp['scan'], fim1_dict) # this depends on what sort of scan it is... how to load this best
        if 'timing' in ssgrp.keys():
            Timing = type('Timing', (Detector,), {})
            self.timing = Timing(grp['timing'], detectors['timing'])



 
