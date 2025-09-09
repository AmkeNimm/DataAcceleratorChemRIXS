from functools import cached_property
from pathlib import Path

import h5py
import yaml
import contextlib
from chemrixs.utils import *
from chemrixs.smalldata import SmallData
import scipy.stats as st

class Reduced():
    """
    A  class for processing the incoming data.

    context manager magic

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

    def __init__(self, path: str | Path | h5py.File, bgpath: str | Path | h5py.File, fyaml: str | Path):
    
        #FIXME: have reduced background saved somewhere?
           
        self.data = SmallData(path,fyaml)
        #load BG data or process it from smalldata and save
        if len(self.data.yaml['red_bg_path']) == 0:
            #process BG
            self.bg = SmallData(bgpath,fyaml)
            self.bg_preproc = False
        else:
            #load BG
            self.bg_preproc = True
            self.bg = None

        self.process_int()

        # if clear_memory == True:
        #     self.data.close()
        #     self.bg.close()
               
      
    def is_open(self) -> bool:
        """
        Function to check whether the file is open.
        """
        if not self.bg_preproc:
            return (self.data.is_open() & self.bg.is_open())
        else:
            return self.data.is_open()

    def __del__(self):
        """
        Function to close the file when the object is deleted.
        """
        if self.data.is_open:
            self.data.close()
        if self.bg.is_open:
            self.bg.close()

    def close(self):
        """
        Function to close the file.
        """
        if self.data.is_open:
            self.data.close()
        if self.bg.is_open:
            self.bg.close()

    def __exit__(self,*exc):
        self.close()

    def __enter__(self):
        self.open()
        return self

    def open(self):  
        """
        Open the file.
        """
        if not self.data.is_open(): 
            self.data.open()
        if not self.bg_preproc and self.bg.is_open():
            self.bg.open()
        else:
            self.bg = h5py.File(self.data.yaml['red_bg_path'], "r")
    
    #def process_ss(self):
        


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

    def process_int(self):
        '''
        parsing function to call the individual processing funcitons for area detectors
        '''

        #COUNTMASK
        if len(self.data.yaml['expected_count']) == 0:
            try:
                expected_count = st.mode(self.data.integrating.andor_vls.count,keepdims=False)[0]
            except:
                expected_count = st.mode(self.data.integrating.axis_svls.count,keepdims=False)[0]
        else:
            expected_count = self.data.yaml['expected_count']
            #FIXME: if the idea is to have the possibility to run integrating detectors at different rates
            #this should be not hard coded for one detector either
        count_mask = (self.data.integrating.andor_vls.count<expected_count+1)&(self.data.integrating.andor_vls.count>expected_count-1)




        #FIXME currently hardcoded the area detectors that are available. If these change, this needs to be fixed

        if 'andor_dir' in self.data.yaml['int_detectors']:
            self.proc_andordir()

        if 'andor_vls' in self.data.yaml['int_detectors']:
            self.proc_andorvls()

        if 'axis_vls' in self.data.yaml['int_detectors']:
            self.proc_svls()
        

    def proc_andorvls(self):



        #SUBTRACT BG
        background_type = self.data.yaml['int_detectors']['andor_vls']['backgroundtype']
        if background_type == 'dark':
            if self.bg_preproc == False:
                if self.bg.integrating.andor_vls.full_area.ndim == 2:
                    self.bg.vls = np.mean(self.bg.integrating.andor_vls.full_area[:,:],0)
                elif self.bg.integrating.andor_vls.full_area.ndim == 3:
                    self.bg.vls = np.mean(self.bg.integrating.andor_vls.full_area[:,:,:],0)
            delattr(self.bg.integrating.andor_vls,'full_area')





        #SUMMING


            # if 'intg' in h5_file.keys():
            #     andor_vls = np.array(h5_file['intg/andor_vls']['full_area'])
            # else:
            #     andor_vls = np.array(h5_file['andor_vls']['grp_intg_full_area'])
        
            # if andor_vls.ndim == 2:
            #     vls_dark_image = np.mean(andor_vls[:,:],0)
            # if andor_vls.ndim == 3:
            #     vls_dark_image = np.mean(andor_vls[:,:,:],0)
            