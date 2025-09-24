
from functools import cached_property
from pathlib import Path

import h5py
import numpy as np
import yaml
from chemrixs.detector import Detector
from chemrixs.utils import *
import scipy.stats as st


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

    Attributes
    ----------
    __getattr__:

    summing_channels:
        reducing fim and apd from multichannel waveforms to integrated value for each shot

    countmask: 
        returns integrated data where frames with faulty number of counts have been filtered out



    Notes:
    ------
    TODO: detectors and keys should be moved to yaml file, then loaded here
    Detector and key names may need to be updated if small data structure changes

    """

    def __init__(self, intgrp: h5py.Group, fyaml: dict, scantype: str = ''):
        self.scantype = scantype
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
        self.countmask()
        # print(sum(self.andor_vls.count_mask))
        self.summing_channels()
        self.get_scanvar()

    def __getattr__(self, name):
        #This will create an error if detector is not in the small data file
        if name in self.yaml['int_detectors']:
            raise KeyError(f'{name} is not in this file')
        return super().__getattribute__(name)
    
    def summing_channels(self):
        '''
        Calling function to integrate the waveform for all waveform detectors
        
        These detectors include APDs and fims.
        '''

        for detector in self.yaml['int_detectors']: 
            det = getattr(self,detector)
            sum_channels(det, self.yaml)
            
            #'clearing cache'
            for channel in self.yaml['channels_to_integrate']:
                delattr(getattr(self, detector),channel)

            #combine fim1 and fim0 to I0
            if (hasattr(det,'fim_0') and hasattr(det,'fim_1')):
                I0 = det.fim0.copy()+det.fim1.copy()
                setattr(det,'I0',I0)
                delattr(det,'fim0')
                delattr(det,'fim1')
            elif hasattr(det,'fim0'):
                I0 = det.fim0.copy()
                setattr(det,'I0',I0)
                delattr(det,'fim0')
            elif hasattr(det,'fim1'):
                I0 = det.fim0.copy()
                setattr(det,'I0',I0)
                delattr(det,'fim1')


   
    def countmask(self):
        '''
        Function to filter on the counts per integrated frame

        every integratind fram should include the same number of shots
        for some frames this will not be the case due to various issues,
        these frames should be filtered out for all detectors
        '''
            
        for detector, det_spec_dict in self.yaml['int_detectors'].items(): 

            det=getattr(self,detector)

            if len(self.yaml['expected_count']) == 0:
                try:
                    expected_count = st.mode(det.count, keepdims=False)[0]
                except:
                    expected_count = st.mode(det.count, keepdims=False)[0]
            else:
                expected_count = self.yaml['expected_count']
            det.count_mask = (det.count<expected_count+2)&(det.count>expected_count-2)

            for at in self.yaml[det_spec_dict['attrdict']]:
                a = getattr(det,at)
                a = a[det.count_mask]
                setattr(det, at, a)

    def get_scanvar(self):
        if (self.scantype=='mono' or self.scantype=='mono_fly'):
            if len(self.yaml['mono_calib'])==0:
                print('mono is not calibrated')
            else:
                for detector in self.yaml['int_detectors']: 
                    det = getattr(self,detector)
                    #for integrating detectors, the mono encoder value is the sum over all shots
                    hrencoder = getattr(det,'mono_encoder')/getattr(det,'count')
                    mono = np.polyval(self.yaml['mono_calib'],hrencoder)
                    setattr(det, 'mono', mono)
                    
        elif self.scantype==('delay' or 'delay_fly'):
            #FIXME
            delay = []
            setattr(det, 'delay', delay)

            
