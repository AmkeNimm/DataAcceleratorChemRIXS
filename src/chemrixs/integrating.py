
from functools import cached_property
from pathlib import Path

import h5py
import numpy as np
import yaml
from chemrixs.detector import Detector

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

axis_svls_dict = {
    'count': 'count',
    'full_area': 'full_area',
}

detectors = {
    'andor_dir': {'attrdict': andor_dir_dict, 'clsname': 'AndorDir', 'useDask': False, 'chunks':()},
    'andor_vls': {'attrdict': andor_vls_dict, 'clsname': 'AndorVLS', 'useDask': False, 'chunks':()},
    'axis_svls': {'attrdict': axis_svls_dict, 'clsname': 'AxisSVLS', 'useDask': False, 'chunks':()},
}



class Integrating():

    
    """
    Class that is called by the small data class to load data from the integrating detectors.

    This class loads data through the Detector class as cached property -
    That way the data is only loaded once it is actually called. This makes it much faster to perform
    small tasks where simple metadata is required, rather than reading in the whole
    header.

    In this class the detectors to be loaded and the respective keys are being defind.

    Anything that is read in is stored in memory so the second access is much faster.
    However, the memory can be released simply by deleting the attribute (it can be
    accessed again, and the data will be re-read).


    Parameters:
    -----------
    intgrp: h5py.Group
        group containing the integrating data defined in the smalldata class

    Notes:
    ------
    TODO: detectors and keys should be moved to yaml file, then loaded here
    Detector and key names may need to be updated if small data structure changes

    """

    def __init__(self, intgrp: h5py.Group):
        for detector in detectors:
            if detector in intgrp.keys():
                #Creating a different class for each detector to avoid printing of attributes on all of them
                detobj = type(detectors[detector]["clsname"], (Detector,), {})
                #Create an attribute for each detector which will in turn will have attributes for the keys specified in the dictionary
                setattr(self, detector, detobj(intgrp[detector], detectors[detector]['attrdict'],useDask=detectors[detector]['useDask'],chunks=detectors[detector]['chunks']))

    def __getattr__(self, name):
        #This will create an error if detector is not in the small data file
        if name in detectors:
            raise KeyError('{name} is not in this file')
        return super().__getattribute__(name)
    