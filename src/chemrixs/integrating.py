
from functools import cached_property
from pathlib import Path

import h5py
import numpy as np
import yaml
from chemrixs.detector import Detector
from chemrixs.utils import *


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

    def __init__(self, intgrp: h5py.Group, fyaml: dict):
        self.yaml = fyaml
        for detector, det_spec_dict in self.yaml['int_detectors'].items():
            if detector in intgrp.keys():
                #Creating a different class for each detector to avoid printing of attributes on all of them
                detobj = type(det_spec_dict["clsname"], (Detector,), {})
                #Create an attribute for each detector which will in turn will have attributes for the keys specified in the dictionary
                setattr(
                    self,
                    detector,
                    detobj(
                        intgrp[detector],
                        self.yaml[det_spec_dict['attrdict']],
                        useDask=det_spec_dict['useDask'],
                        chunks=det_spec_dict['chunks']
                    )
                )
        self.summing_channels()
        self.process_area_detectors()

    def __getattr__(self, name):
        #This will create an error if detector is not in the small data file
        if name in self.yaml['int_detectors']:
            raise KeyError(f'{name} is not in this file')
        return super().__getattribute__(name)
    
    def summing_channels(self):

        for detector in self.yaml['int_detectors']: 
            sum_channels(getattr(self,detector), self.yaml)
            #'clearing cache'
            for channel in self.yaml['channels_to_integrate']:
                delattr(getattr(self, detector),channel)

    def process_area_detectors(self):
        #FIXME currently hardcoded the area detectors that are available. If these change, this needs to be fixed

        if 'andor_dir' in self.yaml['int_detectors']:
            #proc_andordir(self,fyaml)
            getattr((self.andor_dir),'full_area')
            delattr((self.andor_dir),'full_area')

        if 'andor_vls' in self.yaml['int_detectors']:
            getattr((self.andor_vls),'full_area')
            delattr((self.andor_vls),'full_area')


        if 'axis_vls' in self.yaml['int_detectors']:
            getattr((self.axis_vls),'full_area')
            delattr((self.axis_vls),'full_area')
            
