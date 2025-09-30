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
                 fyaml: str | Path, bgyaml: str | Path, scantype: str = '',norm: bool = True):
        self.scantype = scantype
        self.norm = norm
        self.data = SmallData(path, fyaml, scantype)
        self.proc = {}
        #load BG data or process it from smalldata and save
        if len(self.data.yaml['red_bg_path']) == 0: #process BG
            self.bg = SmallData(bgpath,bgyaml,scantype)
            self.bg_preproc = False
        else: #load BG from preprocessed file
            #FIXME: how does preprocessed file look? make sure everything necessary is there
            self.bg_preproc = True
            self.bg = None

        self.process_int()

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
        
        #self.bin_intdet()
        

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
        elif background_type == 'None':
            self.bg.vls = np.zeros(self.data.integrating.andor_vls.full_area.shape[:-2],0)
            

        #SUBTRACT BG AND THRESHOLD
            #FIXME: is full are the variable that is changing shape from 2 to 3?
            if self.data.integrating.andor_vls.full_area.ndim == 2:
                vls_dark_subtracted = self.data.integrating.andor_vls.full_area#-self.bg.vls[np.newaxis,:]
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
        self.proc['axis_dir']['on'] = []
        self.proc['axis_dir']['off'] = []

    def proc_svls(self):
        background_type = self.data.yaml['int_detectors']['andor_vls']['backgroundtype']
        offset_roi = self.data.yaml['svls']['offset_roi']

        #PROCESS BG
        if background_type == 'dark':
            if self.bg_preproc == False:
                if self.bg.integrating.axis_svls.full_area.ndim == 2:
                    self.bg.svls = np.mean(self.bg.integrating.axis_svls.full_area[:,:],0)
                    svls_proc = self.data.integrating.axis_svls.full_area-self.bg.svls[np.newaxis,:]
                elif self.bg.integrating.andor_vls.full_area.ndim == 3:
                    self.bg.svls = np.mean(self.bg.integrating.axis_svls.full_area[:,:,:],0)
                    svls_proc = self.data.integrating.axis_svls.full_area-self.bg.svls[np.newaxis,:,:]
            delattr(self.bg.integrating.axis_svls,'full_area')

        elif background_type == 'None':
            svls_dark_subtracted = np.zeros(self.data.integrating.axis_svls.full_area.shape[-2:],0)
            delattr(self.bg.integrating.axis_svls,'full_area')

        elif background_type == 'ROI':
            if self.data.integrating.axis_svls.full_area.ndim == 2:
                offset_background = np.nanmean(svls_dark_subtracted[:,offset_roi[0]:offset_roi[1]],1)
                svls_background_subtracted = svls_dark_subtracted - offset_background[:,np.newaxis]
                svls_proc = np.flip(svls_background_subtracted,1)
            elif self.data.integrating.axis_svls.full_area.ndim == 3:
                #FIXME: still needs to be implemented
                print('need to implement BG subtraction for full image SVLS')
            delattr(self.bg.integrating.axis_svls,'full_area')

        #Normalise detectors to I0 from fims
        I0 = self.data.integrating.axis_svls.I0
        if self.norm == True:    
            norm_svls = normalise(svls_proc,I0)
        else:                 
            norm_svls = vls_proc

        self.proc['axis_svls'] = {}
        self.proc['axis_svls']['on'] = norm_svls[self.data.integrating.axis_svls.eventcodes[:,self.data.yaml['evc'][True]]==True] #weird ymal magic turns 'on' automatically into True
        self.proc['axis_svls']['off'] = norm_svls[self.data.integrating.axis_svls.eventcodes[:,self.data.yaml['evc'][False]]==True] #weird ymal magic turns 'off' automatically into False


# def process_SVLS(count_masked_data,background,threshold=True,threshold_min=15,threshold_max=500):
#     background_type = background[0]

#     axis_svls = count_masked_data['svls']
#     svls_offset_roi = background[3]
#     if background_type == 'dark':
#         print('Subtracting dark')
#         dark = svls_dark(background)
#         if axis_svls.ndim == 3:
#             try:
#                 svls_dark_subtracted = axis_svls-dark[np.newaxis,:,:]
#             except:
#                 print('Background does not match the shape of the detector, no background has been subtracted')
#                 svls_dark_subtracted = axis_svls
#         elif axis_svls.ndim == 2:
#             try:
#                 svls_dark_subtracted = axis_svls-dark[np.newaxis,:]
#             except:
#                 print('Background does not match the shape of the detector, no background has been subtracted')
#                 svls_dark_subtracted = axis_svls
#     else:
#         print('No dark subtracted')
#         svls_dark_subtracted = axis_svls
#     if background_type == 'offset':
#         if axis_svls.ndim == 3:
#             svls_proc = np.nansum(svls_dark_subtracted,2)
#             if 'scan_var' in count_masked_data.keys():
#                 scan_var = count_masked_data['scan_var']
    
#                 fig,ax = plt.subplots(1,3,figsize=(10,5))
#                 ax[0].plot(np.mean(axis_svls[:,:,:][scan_var==np.max(scan_var)],(0,2)),label='%s'%np.max(scan_var))
#                 ax[0].plot(np.mean(axis_svls[:,:,:][scan_var==np.min(scan_var)],(0,2)),label='%s' %np.min(scan_var))
#                 ax[0].plot(np.mean(dark,1),label='dark')
#                 ax[0].set_xlabel('pixel')
#                 ax[0].set_title('Pre background corrections')
#                 ax[0].legend()
                
#                 ax[1].plot(np.mean(axis_svls[:,:,:][scan_var==np.max(scan_var)],(0,2))-np.mean(dark,1),label='%s'%np.max(scan_var))
#                 ax[1].plot(np.mean(axis_svls[:,:,:][scan_var==np.min(scan_var)],(0,2))-np.mean(dark,1),label='%s' %np.min(scan_var))
#                 ax[1].set_xlabel('pixel')
#                 ax[1].set_title('Dark corrected')
#                 ax[1].legend()
                
                
#                 ax[2].plot(np.mean(svls_background_subtracted[:,:,:][scan_var==np.max(scan_var)],(0,2)),label='%s'%np.max(scan_var))
#                 ax[2].plot(np.mean(svls_background_subtracted[:,:,:][scan_var==np.min(scan_var)],(0,2)),label='%s'%np.min(scan_var))
#                 ax[2].set_xlabel('pixel')
#                 ax[2].set_title('Dark and Offset corrected')
#                 ax[2].legend()
    
#         if axis_svls.ndim == 2:
#             offset_background = np.nanmean(svls_dark_subtracted[:,svls_offset_roi[0]:svls_offset_roi[1]],1)
#             svls_background_subtracted = svls_dark_subtracted - offset_background[:,np.newaxis]
#             svls_proc = np.flip(svls_background_subtracted,1)

#     if background_type == 'None':
#         svls_proc = np.flip(axis_svls,1)

        
#     return svls_proc

    def bin_intdet(self):
        #FIXME: this is only binning the integrating detector itseld - associated variables also need to be binned (fims etc)
        for detector, det_spec_dict in self.data.yaml['int_detectors'].items():
            det = getattr(self.data.integrating,detector)
            evc = getattr(det, 'eventcodes')
            onmask = (evc[:,272]==1)
            offmask = (evc[:,273]==1)
            print(det)

            norm_on = self.proc[detector]['on']
            norm_off = self.proc[detector]['off']
   
            #FIXME: do I cover all potential scan types?
            #static scan
            if self.data.runinfo == 'static':
                print('static run!')
                tmp_on = np.nanmean(norm_on,axis=0)
                tmp_off = np.nanmean(norm_off,axis=0)
                setattr(self,detector+'_on',tmp_on)
                setattr(self,detector+'_off',tmp_off)

            #step scans
            elif (self.scantype=='mono' or self.scantype=='delay'):
                print('step scan!')
                if self.scantype=='mono':
                    scanvar = getattr(det,'mono')
                elif self.scantype=='delay':
                    scanvar = getattr(det,'delay')
                    
                scanvar_on, tmp_on_sum, tmp_on_mean, tmp_on_std = bin_data(norm_on,scanvar[onmask],bins=self.data.yaml['bins'],scantype='step')
                scanvar_off, tmp_off_sum, tmp_off_mean, tmp_off_std = bin_data(norm_off,scanvar[offmask],bins=self.data.yaml['bins'],scantype='step')
                
                setattr(self,detector+'_on',tmp_on)
                setattr(self,detector+'_off',tmp_off)
                setattr(self,'scanvar_on',scanvar_on)
                setattr(self,'scanvar_off',scanvar_off)
        
        
        
            #fly scans
            elif (self.scantype=='mono_fly' or self.scantype=='delay_fly'):    
                print('fly scan!')
                if self.scantype=='delay_fly':
                    scanvar = getattr(det,'delay')
                elif self.scantype=='mono_fly':
                    scanvar = getattr(det,'mono')
                scanvar_on, tmp_on_sum, tmp_on_mean, tmp_on_std = bin_data(norm_on,scanvar[onmask],bins=self.data.yaml['bins'],scantype='fly')
                scanvar_off, tmp_off_sum, tmp_off_mean, tmp_off_std = bin_data(norm_off,scanvar[offmask],bins=self.data.yaml['bins'],scantype='fly')
   
                setattr(self,detector+'_on_sum',tmp_on_sum)
                setattr(self,detector+'_off_sum',tmp_off_sum)
                setattr(self,detector+'_on_mean',tmp_on_mean)
                setattr(self,detector+'_off_mean',tmp_off_mean)
                setattr(self,detector+'_on_std',tmp_on_std)
                setattr(self,detector+'_off_std',tmp_off_std)
                setattr(self,'scanvar_on',scanvar_on)
                setattr(self,'scanvar_off',scanvar_off)
        
            else:
                print('runtype unknown')
