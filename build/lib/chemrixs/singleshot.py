
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

detectors = {
             'c_piranha': {'attrdict': piranha_dict, 'clsname': 'Piranha', 'useDask': True, 'chunks':(1000)},
             'det_crix_w8': {'attrdict': apds_dict, 'clsname': 'APDs', 'useDask': True, 'chunks':(1000)},
             'det_rix_fim0': {'attrdict': fim0_dict, 'clsname': 'FIM0', 'useDask': True, 'chunks':(1000)},
             'det_rix_fim1': {'attrdict': fim1_dict, 'clsname': 'FIM1', 'useDask': True, 'chunks':(1000)},
             'lightStatus': {'attrdict': lightstatus_dict, 'clsname': 'Light', 'useDask': True, 'chunks':(1000)},
             'mono_hrencoder': {'attrdict': encoder_dict, 'clsname': 'Mono', 'useDask': True, 'chunks':(1000)},
             'timing': {'attrdict': timing_dict, 'clsname': 'Timing', 'useDask': True, 'chunks':(1000)}
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

        for detector in detectors:
            if detector in ssgrp.keys():
                detobj = type(detectors[detector]["clsname"], (Detector,), {})
                setattr(self, detector, detobj(ssgrp[detector], detectors[detector]['attrdict'],useDask=detectors[detector]['useDask'],chunks=detectors[detector]['chunks']))

    def __getattr__(self, name):
        print(name)
        if name in detectors:
            raise KeyError('{name} is not in this file')
        return super().__getattribute__(name)