from functools import cached_property
from pathlib import Path

import h5py
import yaml
import contextlib
from chemrixs.utils import *
from chemrixs.smalldata import SmallData
import scipy.ndimage as ndimage

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

    def __init__(self, path: str | Path | h5py.File, bgpath: str | Path | h5py.File, 
                 fyaml: str | Path, scantype: str = '',norm: bool = True):
        self.scantype = scantype
        self.norm = norm
        self.data = SmallData(path, fyaml, scantype)
        self.proc = {}
        #load BG data or process it from smalldata and save
        if len(self.data.yaml['red_bg_path']) == 0: #process BG
            self.bg = SmallData(bgpath,fyaml,scantype)
            self.bg_preproc = False
        else: #load BG from preprocessed file
            #FIXME: how does preprocessed file look? make sure everything necessary is there
            self.bg_preproc = True
            self.bg = None

        self.process_int()
        self.bin_intdet()

        #FIXME: do we want a manual clear memory option?
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

        #FIXME currently hardcoded the area detectors that are available. If these change, this needs to be fixed

        if 'andor_dir' in self.data.yaml['int_detectors']:
            self.proc_andordir()

        if 'andor_vls' in self.data.yaml['int_detectors']:
            self.proc_andorvls()

        if 'axis_svls' in self.data.yaml['int_detectors']:
            self.proc_svls()
        

    def proc_andorvls(self):
        '''
        Function to process the VLS detector

        Flexible implementation for data being provided 2D or 3D, different types of background
        subtractions are chosen in the input yaml file

        Paramters are defined in input yaml file
        '''

        background_type = self.data.yaml['int_detectors']['andor_vls']['backgroundtype']
        roi = self.data.yaml['andor_vls']['roi']
        threshold = self.data.yaml['andor_vls']['threshold']
        


        #PROCESS BG
        if background_type == 'dark':
            if self.bg_preproc == False:
                if self.bg.integrating.andor_vls.full_area.ndim == 2:
                    self.bg.vls = np.mean(self.bg.integrating.andor_vls.full_area[:,:],0)
                elif self.bg.integrating.andor_vls.full_area.ndim == 3:
                    self.bg.vls = np.mean(self.bg.integrating.andor_vls.full_area[:,:,:],0)
            delattr(self.bg.integrating.andor_vls,'full_area')
            

        #SUBTRACT BG AND THRESHOLD
            #FIXME: is full are the variable that is changing shape from 2 to 3?
            if self.data.integrating.andor_vls.full_area.ndim == 2:
                vls_dark_subtracted = self.data.integrating.andor_vls.full_area-self.bg.vls[np.newaxis,:]
                offset_background = np.nanmean(vls_dark_subtracted[:,roi[0]:roi[1]],1)
                vls_background_subtracted = vls_dark_subtracted - offset_background[:,np.newaxis]
                
                astd,amean = vls_background_subtracted[:,roi[0]:roi[1]].std(),vls_background_subtracted[:,roi[0]:roi[1]].mean()
                vls_proc = vls_background_subtracted.copy()
                vls_proc[vls_proc<(threshold[0]*astd)] = 0
                vls_proc[vls_proc>threshold[1]] = 0

            elif self.data.integrating.andor_vls.full_area.ndim == 3:

                vls_dark_subtracted = self.data.integrating.andor_vls.full_area-self.bg.vls[np.newaxis,:,:]
                offset_background = np.nanmean(vls_dark_subtracted[:,roi[2]:vls_offset_roi[3],roi[0]:roi[1]],(1,2))
                vls_background_subtracted = vls_dark_subtracted - offset_background[:,np.newaxis,np.newaxis]

                vls_unrotated = vls_background_subtracted.copy()
                vls_unrotated[vls_unrotated<threshold[0]] = 0
                vls_unrotated[vls_unrotated>threshold[1]] = 0
                    
                vls_rotated = ndimage.rotate(vls_unrotated,self.data.yaml['andor_vls']['rot_angle'],order=3,axes = (2,1),cval=0)
                vls_cropped = vls_rotated[:,self.data.yaml['andor_vls']['rot_crop'][0]:self.data.yaml['andor_vls']['rot_crop'][1],:]
                vls_proc = np.sum(vls_cropped,axis=2)

            else:
                print('Andor VLS format unknown')

          #Normalise detectors to I0 from fims
            I0 = self.data.integrating.andor_vls.I0
            if self.norm == True:    
                norm_vls = normalise(vls_proc,I0)
            else:                 
                norm_vls = vls_proc
            
            self.proc['andor_vls'] = {}            
            self.proc['andor_vls']['on'] = norm_vls[self.data.integrating.andor_vls.eventcodes[:,self.data.yaml['evc'][True]]==True] #weird ymal magic turns 'on' automatically into True
            self.proc['andor_vls']['off'] = norm_vls[self.data.integrating.andor_vls.eventcodes[:,self.data.yaml['evc'][False]]==True]

    def proc_andordir(self):
        self.proc['andor_dir'] = {}
        self.proc['axis_svls']['on'] = []
        self.proc['axis_svls']['off'] = []

    def proc_svls(self):
        self.proc['axis_svls'] = {}
        self.proc['axis_svls']['on'] = []
        self.proc['axis_svls']['off'] = []

    def bin_intdet(self):
        #FIXME: this is only binning the integrating detector itseld - associated variables also need to be binned (fims etc)
        for detector, det_spec_dict in self.data.yaml['int_detectors'].items():
            det = getattr(self.data.integrating,detector)
            print(det)
   
            #FIXME: do I cover all potential scan types?
            #static scan
            if self.data.runinfo == 'static':
                tmp_on = np.nanmean(norm_on,axis=0)
                tmp_off = np.nanmean(norm_off,axis=0)
                setattr(self,detector+'_on',tmp_on)
                setattr(self,detector+'_off',tmp_off)

            #step scans
            elif (self.scantype=='mono' or self.scantype=='delay'):
                if self.scantype=='mono':
                    scanvar = getattr(det,'mono')
                elif self.scantype=='delay':
                    scanvar = getattr(det,'delay')
                scanvar_uni = np.unique(scanvar)
                inds = np.digitize(np.round(scanvar,4),scanvar_uni)
        
        
        
            #fly scans
            elif (self.scantype=='mono_fly'):
                tmp_on = np.nanmean(self.proc[detector]['on'],axis=0)
                tmp_off = np.nanmean(self.proc[detector]['off'],axis=0)
                setattr(self,detector+'_on',tmp_on)
                setattr(self,detector+'_off',tmp_off)
        
            elif (self.scantype=='delay_fly'):
                tmp_on = np.nanmean(self.proc[detector]['on'],axis=0)
                tmp_off = np.nanmean(self.proc[detector]['off'],axis=0)
                setattr(self,detector+'_on',tmp_on)
                setattr(self,detector+'_off',tmp_off)
        
        else:
            print('runtype unknown')
