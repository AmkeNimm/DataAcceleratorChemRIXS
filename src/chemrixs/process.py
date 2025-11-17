from functools import cached_property
from pathlib import Path

import h5py
import yaml
import contextlib
from chemrixs.utils import *
from chemrixs.smalldata import SmallData
import scipy.ndimage as ndimage
import os

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
                 fyaml: str | Path, bgyaml: str | Path, save: bool = True, scantype: str = '',norm: bool = True):
        self.scantype = scantype
        self.norm = norm
        self.data = SmallData(path, fyaml, scantype)
        self.proc = {}
        #load BG data or process it from smalldata and save
        if os.path.isfile(self.data.yaml['red_bg_path']): #load BG from preprocessed file
            #FIXME: how does preprocessed file look? make sure everything necessary is there
            self.bg_preproc = True
            self.bg = BG(self.data.yaml['red_bg_path'])
            
        else: #process BG
            self.bg_preproc = False
            self.bg = SmallData(bgpath,bgyaml,'static')

        self.process_int()
        # print(self.data.epics())
        if save ==True:
            self.save_dat()
            print('saved processed data')
            if self.bg_preproc == False:
                self.save_bg()

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
        
        self.bin_intdet()
        

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
                getattr(self.bg.integrating.andor_vls,'full_area')
                self.bg.vls = np.nanmean(self.bg.integrating.andor_vls.full_area,0)
                delattr(self.bg.integrating.andor_vls,'full_area')
            else:
                self.bg.vls = np.asarray(self.bg.file['andor_vls'])

        elif background_type == 'None':
            self.bg.vls = np.zeros(self.data.integrating.andor_vls.full_area.shape[:-2])
            

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
            vls_proc = np.nansum(vls_cropped,axis=2)

        else:
            print('Andor VLS format unknown')

        #Normalise detectors to I0 from fims
        I0 = self.data.integrating.andor_vls.I0
        if self.norm == True:    
            norm_vls = normalise(vls_proc,I0)
        else:                 
            norm_vls = vls_proc

        evc_on = self.data.integrating.axis_svls.eventcodes[:,self.data.yaml['evc'][True]]
        evc_off = self.data.integrating.axis_svls.eventcodes[:,self.data.yaml['evc'][False]]
   
        self.proc['andor_vls'] = {}            
        self.proc['andor_vls']['on'] = norm_vls[evc_on==True] #weird ymal magic turns 'on' automatically into True
        self.proc['andor_vls']['off'] = norm_vls[evc_off==True]
        if (np.nansum(evc_on)+np.nansum(evc_off))==0:
            self.proc['andor_vls']=norm_vls

    def proc_andordir(self):

        self.proc['andor_dir'] = {}
        self.proc['axis_dir']['on'] = []
        self.proc['axis_dir']['off'] = []

    def proc_svls(self):
        background_type = self.data.yaml['int_detectors']['axis_svls']['backgroundtype']
        offset_roi = self.data.yaml['svls']['offset_roi']
        thresh_min = self.data.yaml['svls']['threshold'][0]
        thresh_max = self.data.yaml['svls']['threshold'][1]

        # self.data.integrating.axis_svls.full_area[self.data.integrating.axis_svls.full_area<thresh_min] = 0
        # self.data.integrating.axis_svls.full_area[self.data.integrating.axis_svls.full_area>thresh_max] = 0
        # self.data.integrating.axis_svls.full_area[np.isnan(self.data.integrating.axis_svls.full_area)] = 0

        #PROCESS BG
        if background_type == 'dark':
            if self.bg_preproc == False:
                # self.bg.integrating.axis_svls.full_area[self.bg.integrating.axis_svls.full_area<thresh_min] = 0
                # self.bg.integrating.axis_svls.full_area[self.bg.integrating.axis_svls.full_area>thresh_max] = 0
                # self.bg.integrating.axis_svls.full_area[np.isnan(self.bg.integrating.axis_svls.full_area)] = 0
                if self.bg.integrating.axis_svls.full_area.ndim == 2:
                    self.bg.svls = np.nanmean(self.bg.integrating.axis_svls.full_area[:,:],0)
                    svls_proc = self.data.integrating.axis_svls.full_area-self.bg.svls[np.newaxis,:]
                elif self.bg.integrating.andor_vls.full_area.ndim == 3:
                    self.bg.svls = np.nanmean(self.bg.integrating.axis_svls.full_area[:,:,:],0)
                    svls_proc = self.data.integrating.axis_svls.full_area-self.bg.svls[np.newaxis,:,:]
            
                delattr(self.bg.integrating.axis_svls,'full_area')
            elif self.bg_preproc == True:
                self.bg.svls = np.asarray(self.bg.file['axis_svls'])
                if self.data.integrating.axis_svls.full_area.ndim == 2:
                    svls_background_subtracted = self.data.integrating.axis_svls.full_area-self.bg.svls[np.newaxis,:]
                    svls_proc = np.flip(svls_background_subtracted,1)
                elif self.data.integrating.andor_vls.full_area.ndim == 3:
                    svls_proc = self.data.integrating.axis_svls.full_area-self.bg.svls[np.newaxis,:,:]
               
        elif background_type == 'None':
            svls_proc = self.data.integrating.axis_svls.full_area
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
            norm_svls = svls_proc
        evc_on = self.data.integrating.axis_svls.eventcodes[:,self.data.yaml['evc'][True]]
        evc_off = self.data.integrating.axis_svls.eventcodes[:,self.data.yaml['evc'][False]]

        self.proc['axis_svls'] = {}
        self.proc['axis_svls']['on'] = norm_svls[evc_on==True] #weird ymal magic turns 'on' automatically into True
        self.proc['axis_svls']['off'] = norm_svls[evc_off==True] #weird ymal magic turns 'off' automatically into False
        if (np.nansum(evc_on)+np.nansum(evc_off))==0:
            self.proc['axis_svls']=norm_svls

    def bin_intdet(self):
        #FIXME: this is only binning the integrating detector itseld - associated variables also need to be binned (fims etc)
        for detector, det_spec_dict in self.data.yaml['int_detectors'].items():
            det = getattr(self.data.integrating,detector)
            evc = getattr(det, 'eventcodes')
            onmask = (evc[:,272]==1)
            offmask = (evc[:,273]==1)
            print(det)

            if (np.nansum(onmask)+np.nansum(offmask))==0:
                norm = self.proc[detector]
            else:
                norm_on = self.proc[detector]['on']
                norm_off = self.proc[detector]['off']

   
            #FIXME: do I cover all potential scan types?
            #static scan
            breakpoint()   
            if self.data.runinfo == 'static':
                print('static run!')
                if (np.nansum(onmask)+np.nansum(offmask))==0:
                    tmp_mean  = np.nanmean(norm,axis=0)
                    tmp_sum = np.nanmsum(norm,axis=0)
                    tmp_std   = np.nanstd(norm,axis=0)
                    
                else:
                    tmp_on_mean  = np.nanmean(norm_on,axis=0)
                    tmp_off_mean = np.nanmean(norm_off,axis=0)
                    tmp_on_sum   = np.nansum(norm_on,axis=0)
                    tmp_off_sum  = np.nansum(norm_off,axis=0)
                    tmp_on_std   = np.nanstd(norm_on,axis=0)
                    tmp_off_std  = np.nanstd(norm_off,axis=0)
                
                run = True

            #step scans
            elif (self.scantype=='mono' or self.scantype=='delay'):
                print('step scan!')
                print(norm_on.shape)
                if self.scantype=='mono':
                    scanvar = getattr(det,'mono')
                elif self.scantype=='delay':
                    scanvar = getattr(det,'delay')
                print(scanvar)
                if (np.nansum(onmask)+np.nansum(offmask))==0:
                    scanvar_bin, tmp_sum, tmp_mean, tmp_std = bin_data(norm,scanvar,bins=self.data.yaml['bins'],scantype='step')
                else:
                    scanvar_on, tmp_on_sum, tmp_on_mean, tmp_on_std = bin_data(norm_on,scanvar[onmask],bins=self.data.yaml['bins'],scantype='step')
                    scanvar_off, tmp_off_sum, tmp_off_mean, tmp_off_std = bin_data(norm_off,scanvar[offmask],bins=self.data.yaml['bins'],scantype='step')
                run =True     
            #fly scans
            elif (self.scantype=='mono_fly' or self.scantype=='delay_fly'):    
                print('fly scan!')
                if self.scantype=='delay_fly':
                    scanvar = getattr(det,'delay')
                elif self.scantype=='mono_fly':
                    scanvar = getattr(det,'mono')
                if (np.nansum(onmask)+np.nansum(offmask))==0:
                    scanvar_bin, tmp_sum, tmp_mean, tmp_std = bin_data(norm,scanvar,bins=self.data.yaml['bins'],scantype='fly')
                else:
                    
                    breakpoint() 
                    scanvar_on, tmp_on_sum, tmp_on_mean, tmp_on_std = bin_data(norm_on,scanvar[onmask],bins=self.data.yaml['bins'],scantype='fly')
                    scanvar_off, tmp_off_sum, tmp_off_mean, tmp_off_std = bin_data(norm_off,scanvar[offmask],bins=self.data.yaml['bins'],scantype='fly')
   
                run =True

        
            else:
                print('runtype unknown')
                run =False

            if not run == False:

                if (np.nansum(onmask)+np.nansum(offmask))==0:
                    setattr(self,detector+'_sum',tmp_sum)
                    setattr(self,detector+'_mean',tmp_mean)
                    setattr(self,'scanvar',scanvar_bin)

                else:
                    setattr(self,detector+'_on_sum',tmp_on_sum)
                    setattr(self,detector+'_off_sum',tmp_off_sum)
                    setattr(self,detector+'_on_mean',tmp_on_mean)
                    setattr(self,detector+'_off_mean',tmp_off_mean)
                    setattr(self,detector+'_on_std',tmp_on_std)
                    setattr(self,detector+'_off_std',tmp_off_std)
                    setattr(self,'scanvar_on',scanvar_on)
                    setattr(self,'scanvar_off',scanvar_off)

    def save_dat(self):
        print('savingdata')
        run = self.data.run
        output = h5py.File(f'./proc/Run{run:04d}.h5','w')
        keys = vars(self)

        for dat in keys:
            if 'on' in dat:
                output.create_dataset(dat,dtype='f',data=keys[dat])
            elif 'off' in dat: 
                output.create_dataset(dat,dtype='f',data=keys[dat])
            elif 'scanvar' in dat: 
                output.create_dataset(dat,dtype='f',data=keys[dat])
            elif 'mean' in dat: 
                output.create_dataset(dat,dtype='f',data=keys[dat])
            elif 'sum' in dat: 
                output.create_dataset(dat,dtype='f',data=keys[dat])
            elif 'std' in dat: 
                output.create_dataset(dat,dtype='f',data=keys[dat])


        output.close()


    def save_bg(self):
        """
        Save processed BG
        """
        if len(self.data.yaml['red_bg_path'])==0:
            bgfname = f'./proc/BG_run{self.bg.run}.h5'
        else:
            bgfname = self.data.yaml['red_bg_path']
        output = h5py.File(bgfname,'w')
        print(self.data.yaml['red_bg_path'])
        if 'andor_dir' in self.data.yaml['int_detectors']:
            output.create_dataset('andor_dir',dtype='f',data=self.bg.dir)
        if 'andor_vls' in self.data.yaml['int_detectors']:
            output.create_dataset('andor_vls',dtype='f',data=self.bg.vls)
        if 'axis_svls' in self.data.yaml['int_detectors']:
            output.create_dataset('axis_svls',dtype='f',data=self.bg.svls)


class BG():
    """
    A  class for passing in previously processed BG data.

    Parameters
    ----------

    bgpath : str or Path
        The filename for a darkscan that can be used for background subtraction.
    """
    def __init__(self,bgpath: str | Path | h5py.File):
        self.file = h5py.File(bgpath,'r')

