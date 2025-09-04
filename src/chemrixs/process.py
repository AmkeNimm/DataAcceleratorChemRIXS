from functools import cached_property
from pathlib import Path

import h5py
import yaml
import contextlib
from chemrixs.utils import *
from chemrixs.smalldata import SmallData

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
axis_svls_dict = andor_dir_dict

detectors = {
#    'andor_dir': {'attrdict': andor_dir_dict, 'clsname': 'AndorDir', 'useDask': False, 'chunks':()},
    'andor_vls': {'attrdict': andor_vls_dict, 'clsname': 'AndorVLS', 'useDask': False, 'chunks':()},
    'axis_svls': {'attrdict': axis_svls_dict, 'clsname': 'AxisSVLS', 'useDask': False, 'chunks':()},
}

channels_to_integrate = {
    'fim_0': 'fim0',
    'fim_1': 'fim1',
    'apds': 'apd'
}

class Reduced():
    """
    A  class for processing the incoming data.

    Parameters
    ----------
    path : str or Path
        The filename for the data to analyse.

    bgpath : str or Path
        The filename for a darkscan that can be used for background subtraction.

    Notes
    -----
    To check if a particular attribute is available, use ``hasattr(obj, attr)``.
    Many attributes will not show up dynamically in an interpreter, because they are
    gotten dynamically from the file.

    TODO: add more error messages for potential failures
    """

    def __init__(self, path: str | Path | h5py.File | h5py.Group, fyaml: str | Path):
        
        self.data = SmallData(path,fyaml)

        # #load BG data or process it from smalldata and save
        # if bgpath.exists():
        #     #load BG
        #     self.bg =  h5py.File(self.bgpath, "r")
        # else:
        #     self.bg = SmallData(bgpath)

            #process BG
        try:
            with open(fyaml, 'r') as file:
                 self.yaml = yaml.safe_load(file)
        except FileNotFoundError as fe: 
            raise FileNotFoundError('Config yaml file not found - check filename') from fe

        

    def process_ss(self):
        
        return 

    # @cached_property
    # def process_int(self):
    #     self.summing_channelsInt(self.yaml)
    
    
    # def check_rois(self):
    #     fig,ax=plt.subplots(1,1)

    # def summing_channelsInt(self,fyaml):
    #     '''
    #     Function to process fim and crix detectors linked to each integrating detector.

    #     Parameters
    #     ----------
    #     fyaml : dictionary containing the ROIs for signal and background
    #     '''

    #     for detector in detectors: 
    #         sum_channels(getattr(self.data.integrating,detector), channels_to_integrate, fyaml)
    #         #'clearing cache'
    #         for channel in channels_to_integrate:
    #             delattr(getattr(self.data.integrating, detector),channel)

    # # def process_area_detector(self,fyaml):
    # #     '''
    # #     '''
    # #     if 'andor_dir' in detectors:
    # #         process_andor_

        

