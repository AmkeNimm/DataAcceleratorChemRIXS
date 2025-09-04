
from functools import cached_property
from pathlib import Path

import h5py
import numpy as np
from chemrixs.detector import Detector
import yaml
from chemrixs.utils import *

# piranha_dict = {'full_area': 'full_area'}
# apds_dict = {'full_area': 'full_area',
#              'preproc': 'wfintegrate'}
# fim0_dict = apds_dict 
# fim1_dict = apds_dict 
# lightstatus_dict = {'laser': 'laser',
#                     'xray': 'xray'}
# encoder_dict = {'mono': 'value'}
# timestamp_dict = {'timestamp': 'timestamp'}
# timing_dict = {'evtcodes': 'eventcodes',
#                'timestamp': 'timestamp'}
# #TODO: somehow the detname for singleshot should be the same as for the integrating detectors
# detectors = {
#              'c_piranha': {'detname': 'piranha', 'attrdict': piranha_dict, 'clsname': 'Piranha', 'useDask': True, 'chunks':(10000)},
#              'det_crix_w8': {'detname': 'apds', 'attrdict': apds_dict, 'clsname': 'APDs', 'useDask': True, 'chunks':(10000)},
#              'det_rix_fim0': {'detname': 'fim_0', 'attrdict': fim0_dict, 'clsname': 'FIM0', 'useDask': True, 'chunks':(10000)},
#              'det_rix_fim1': {'detname': 'fim_1', 'attrdict': fim1_dict, 'clsname': 'FIM1', 'useDask': True, 'chunks':(10000)},
#              'lightStatus': {'detname': 'light', 'attrdict': lightstatus_dict, 'clsname': 'Light', 'useDask': True, 'chunks':(10000)},
#              'mono_hrencoder': {'detname': 'mono_encoder', 'attrdict': encoder_dict, 'clsname': 'Mono', 'useDask': True, 'chunks':(10000)},
#              'timing': {'detname': 'timing', 'attrdict': timing_dict, 'clsname': 'Timing', 'useDask': True, 'chunks':(10000)}
#             }

# channels_to_integrate = {
#     'fim_0': 'fim0',
#     'fim_1': 'fim1',
#     'apds': 'apd'
# }

class Singleshot():
    """
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
        group containing the single shot data defined in the smalldata class

    Notes:
    ------
    TODO: detectors and keys should be moved to yaml file, then loaded here
    Detector and key names may need to be updated if small data structure changes

    """
    def __init__(self, ssgrp: h5py.Group, fyaml: dict):
        self.yaml = fyaml
        for detector in self.yaml['ss_detectors']:
            if detector in ssgrp.keys():
                detobj = type(self.yaml['ss_detectors'][detector]["clsname"], 
                              (Detector,), {})
                setattr(self, 
                        self.yaml['ss_detectors'][detector]['detname'], 
                        detobj(ssgrp[detector], 
                               self.yaml[self.yaml['ss_detectors'][detector]['attrdict']],
                               useDask=self.yaml['ss_detectors'][detector]['useDask'],
                               chunks=int(self.yaml['ss_detectors'][detector]['chunks'])))
        self.summing_channels()

    def __getattr__(self, name):
        """
        Function to print warning in case detector is not in h5 file.

        This function is only called if a specific detector is called but not loaded throught the above init.
        Therefore, if this function is called it means, the detector is not in the h5 file and the error message is printed
        without stopping the entire script.

        Parameters:
        -----------
        name: str
            key for detector
        """
        print(name)
        if name in self.yaml['ss_detectors']:
            raise KeyError('{name} is not in this file')
        return super().__getattribute__(name)
    

    def process(self):
        """
        Overall function to process incoming data, this includes filtering 
        on I0 and mismatches in data
        
        Parameters
        ----------
        rois : dictionary
            Containing ROIs for different detectors.
        

        Notes
        -----
        To check if a particular attribute is available, use ``hasattr(obj, attr)``.
        Many attributes will not show up dynamically in an interpreter, because they are
        gotten dynamically from the file.
        
        """
        # with open('../roi_input.yml', 'r') as file:
        #     rois = yaml.safe_load(file)
        

    #FIXME : how to call sum_channels function properly??
    def summing_channels(self):
        sum_channels(self, self.yaml)
        #'clearing cache'
        for channel in self.yaml['channels_to_integrate']:
            delattr(self,channel)
        # if hasattr(self,'fim_0'):
        #     self.fim0 = sum_channels(self.fim_0.preproc,self.rois['fim0'])
        # if hasattr(self,'fim_1'):
        #     self.fim1 = sum_channels(self.fim_1.preproc,self.rois['fim1'])
        # if hasattr(self,'apds'):
        #     self.apd = sum_channels(self.apds.preproc,self.rois['APDs'])
        # #TODO: delete processed variables from memory here?