
from functools import cached_property
from pathlib import Path

import h5py
import numpy as np
from chemrixs.detector import Detector
import yaml
from chemrixs.utils import *


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
    
        

    def summing_channels(self):
        #FIXME: check rep arte to see if dask arrays are needed 
        '''
        Function to process fims and APDs, raw data cached property
        is removed from memory after processing but can still be called
        '''
        sum_channels(self, self.yaml)
        #'clearing cache'
        for channel in self.yaml['channels_to_integrate']:
            delattr(self,channel)
    