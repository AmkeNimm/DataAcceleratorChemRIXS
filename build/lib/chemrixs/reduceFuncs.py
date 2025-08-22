import time
import h5py
import numpy as np
import matplotlib.pyplot as plt
cmap = plt.cm.get_cmap('terrain').reversed()
import scipy.stats as st
from scipy.optimize import curve_fit
#from scipy.ndimage import rotate
import dask.array as da
import dask.dataframe as dd
import psutil
from distributed import LocalCluster, Client
from dask_jobqueue.slurm import SLURMCluster
import os
import sys
#from chemRIXSAnalysis_BIP import *
from scipy.stats import binned_statistic
#from helper_funcs_AN import load_data
#from helper_funcs_AN import *
from scipy import ndimage



class chemRIXSdat:

    def __init__(self, exp, run,run_dark, acq,exp_c):
        self.exp = exp
        self.run = run
        self.run_dark = run_dark
        self.acq = acq
        self.exp_c = exp_c
        self.base_folder = '/sdf/data/lcls/ds/rix/'

    
    def init_data(self):
        exp = self.exp
        run = self.run
        #load data for specific run 
        fname = f'{self.base_folder}/{exp}/hdf5/smalldata/{exp}_Run{run:04d}.h5'
        fh = h5py.File(fname, 'r')
        self.dat = load_data(run, fh, chunks = 'auto', load_ttfex = True, evc_laser_on = 272,acq='ss')

        run_dark=self.run_dark
        darkname = f'{self.base_folder}/{exp}/hdf5/smalldata/{exp}_Run{run_dark:04d}.h5'
        fh_dark = h5py.File(darkname, 'r')
        self.bg = load_data(run_dark, fh_dark, chunks = 'auto', load_ttfex = True, evc_laser_on = 272,acq='ss')
        #define scan type
        if 'scan' in fh.keys():
            if 'mono_ev' in fh['scan']:
                self.scantype = 'mono'
            elif 'lxt_ttc' in fh['scan']:
                self.scantype = 'lxt_ttc'
            else:
                print('Scantype unknown')
        else:
            self.scantype = 'single'
        #load ROIs and relevant channels - to be checked at beginning of experiment
        self.rois, self.channels = load_ROIS()
        print('loaded data')

    def get_I0filter(self):
        #Filtering out everything outside 1.5sigma of the Izero distribution - consider readjusting 1.5
        if self.acq=='ss':
            self.dat['Izero'] = calc_IZero(self.dat['fim0_wf_ss'], self.dat['fim1_wf_ss'], self.rois, self.channels)
            mean = self.dat['Izero'].mean()
            stdI0 = self.dat['Izero'].std()
            I0_min = mean - 5*stdI0
            I0_max = mean + 5*stdI0
            self.dat['I0_filter'] = np.logical_and((self.dat['Izero']>I0_min),(self.dat['Izero']<I0_max))
            
            #goose/ungoose filterstamps:
            self.dat['goose'] = self.dat['evc_ss'][:,272].round().astype('bool')
            self.dat['no_goose'] = self.dat['evc_ss'][:,273].round().astype('bool')
            
        elif self.acq=='int':
            #Filter on mismatch in timestamps
            try:
                self.dat['timestamp_filter'] = np.asarray(np.ones(self.dat['vls_timestamp'].shape),dtype=bool) #np.asarray(timestamp_filter)

            
                #Filter on expected count
                self.dat['count_mask'] = (self.dat['count_int'].compute()==self.exp_c)
            except:
                print('could not determin count mask')
            try:   
                Izero0 = calc_IZero(self.dat['fim0_wf_int'], self.dat['fim1_wf_int'], self.rois, self.channels)
                mean = np.nanmean(Izero0)
                stdI0 = np.std(Izero0)
                I0_min = mean - 2*stdI0
                I0_max = mean + 2*stdI0
                I0_filter = np.logical_and((Izero0>I0_min),(Izero0<I0_max))
                self.dat['I0_filter'] = I0_filter[self.dat['count_mask'][self.dat['timestamp_filter']]]
                self.dat['Izero'] = Izero0[self.dat['count_mask'][self.dat['timestamp_filter']]]
            except:
                print('could not calc I0')

            try:
                #goose/ungoose filterstamps:
                self.dat['goose'] = self.dat['evc_int'][:,272].round().astype('bool')[self.dat['count_mask'][self.dat['timestamp_filter']]]
                self.dat['no_goose'] = self.dat['evc_int'][:,273].round().astype('bool')[self.dat['count_mask'][self.dat['timestamp_filter']]]

            except:
                print('wild goose chase failed')
        print('I0 filter')

    def get_APDfiltered(self):
        if self.acq=='ss':
            self.dat['apd_sum'] = sum_apd(self.dat['apd_wf_ss'], self.rois, self.channels)
        elif self.acq=='int':
            apd_sum = sum_apd(self.dat['apd_wf_int'], self.rois, self.channels)
            self.dat['apd_sum'] = apd_sum[self.dat['count_mask'][self.dat['timestamp_filter']]]

        #self.dat['apd_on'] = self.dat['apd_sum'][np.logical_and(self.dat['I0_filter'], self.dat['no_goose'])]
        #self.dat['apd_off'] = self.dat['apd_sum'][np.logical_and(self.dat['I0_filter'], self.dat['goose'])]
        #self.dat['I0_on'] = self.dat['Izero'][np.logical_and(self.dat['I0_filter'], self.dat['no_goose'])]
        #self.dat['I0_off'] = self.dat['Izero'][np.logical_and(self.dat['I0_filter'], self.dat['goose'])]
        self.dat['apd_I0corr'] = self.dat['apd_sum']/self.dat['Izero']
        print('reduced APDs')
        
    def get_int(self):
        
        if self.dat['vls'].ndim == 3:
            self.get_vls2D()
            self.get_dir2D()
        else:
            self.get_vls1D()  
            self.get_dir1D()  
        self.get_SVLS()
        print('processed integrating detectors')
        
    def get_SVLS(self):
        vls_offset_roi = self.rois['svls']
        svls_raw = self.dat['svls'][np.logical_and(self.dat['timestamp_filter'],self.dat['count_mask']),:,:]
        if svls_raw.ndim == 3:
            svls_dark = np.nanmean(self.bg['svls'],axis=0) 
            try:
                svls_bgf = svls_raw #- svls_dark[np.newaxis,:,:]
            except:
                print('SVLS and BG size do not match')
                svls_bgf = svls_raw 
            
            self.dat['svls_sum'] = da.squeeze(np.nansum(svls_bgf,axis=2))
        
        elif self.dat['svls'].ndim == 2:
            svls_dark = np.nanmean(data.bg['svls'],axis=0)
            svls_raw = self.dat['svls'][np.logical_and(self.dat['timestamp_filter'],self.dat['count_mask']),:]
            try:
                svls_bgf = svls_raw - svls_dark[np.newaxis,:]
            except:
                print('SVLS and BG size do not match')
                svls_bgf = svls_raw
                    
            offset_background = np.nanmean(svls_bgf[:,svls_offset_roi[0]:svls_offset_roi[1]],1)
            svls_background_subtracted = svls_bgf - offset_background[:,np.newaxis]
        
            self.dat['svls_sum'] = da.squeeze(np.flip(svls_background_subtracted,1))
    
    def get_vls1D(self, threshold_min=0, threshold_max=1000):   
        # load dark detector image
        vls_bg = np.nanmean(self.bg['vls'],axis=(0))
        
        # subtract dark image from VLS data
        raw_vls = self.dat['vls'][np.logical_and(self.dat['timestamp_filter'],self.dat['count_mask']),:]#[count_mask,:,:]
        vls_subbg = raw_vls-vls_bg[np.newaxis,:]
        
        # subtract constant background from VLS data
        #######
        # vls_offset_roi = [20,100,330,510] # Nitrogen
        vls_offset_roi = [20,100,400,510] # Oxygen
        ########
        offset_roi = vls_subbg[:,self.rois['vls_bg1D'][0]:self.rois['vls_bg1D'][1]]   #vls_subbg[:,vls_offset_roi[2]:vls_offset_roi[3],vls_offset_roi[1]:vls_offset_roi[2]]
        offset_roi[offset_roi>10] = 0 # exclude signals with actual signal
        offset = np.nanmean(offset_roi,1)
        vls_bgf = vls_subbg - offset[:,np.newaxis]
        
        #set threshold for single pixel (bandgap si 3.6eV -> 520eV/3.6eV = int/ph)
        vls_threshold = vls_bgf
        # again set outliers to 0
        vls_threshold[vls_threshold<=threshold_min]=0
        vls_threshold[vls_threshold>=threshold_max]=0
        
        #sum over non energy dispersive axis (axis=2)
        self.dat['vls_sum'] = vls_threshold

    def get_vls2D(self):   
        # load dark detector image
        vls_bg = np.nanmean(self.bg['vls'],axis=(0))

        # subtract dark image from VLS data
        raw_vls = self.dat['vls'][np.logical_and(self.dat['timestamp_filter'],self.dat['count_mask']),:,:]#[count_mask,:,:]
        vls_subbg = raw_vls-vls_bg[np.newaxis,:,:]

        # subtract constant background from VLS data
        offset_roi = vls_subbg[:,self.rois['vls_bg2D'][2]:self.rois['vls_bg2D'][3],self.rois['vls_bg2D'][1]:self.rois['vls_bg2D'][2]]
        offset_roi[offset_roi>100] = 0 # exclude signals with actual signal
        offset = np.nanmean(offset_roi,(1,2))
        vls_bgf = vls_subbg - offset[:,np.newaxis,np.newaxis]
        
        #set threshold for single pixel (bandgap si 3.6eV -> 520eV/3.6eV = int/ph)
        vls_threshold = vls_bgf
        vls_threshold[vls_threshold<15] = 0
        # rotate VLS image
        vls_rotated = ndimage.rotate(vls_threshold,4.5,order=3,axes = (2,1),cval=0)
        # vls_rotated = ndimage.rotate(vls_dark_subtracted,4.5,order=3,axes = (2,1),cval=0)
        
        
        # again set outliers to 0
        vls_rotated[vls_rotated<=3]=0
        vls_rotated[vls_rotated>=120]=0
        
        #crop rotated image
        vls_cropped = vls_rotated[:,11:510,:]
        
        
        #sum over non energy dispersive axis (axis=2)
        self.dat['vls_sum'] = np.nansum(vls_cropped,axis= 2)

    def get_dir2D(self):   
        #load background from dark run and substract
        dir_bg        = np.nanmean(self.bg['dir'],axis=(0))
        raw_dir       = self.dat['dir'][np.logical_and(self.dat['timestamp_filter'],self.dat['count_mask']),:,:]#[count_mask,:,:]
        dir_subbg     = raw_dir-dir_bg[np.newaxis,:,:]
        #thresholding
        dir_threshold = dir_subbg
        dir_threshold[dir_threshold<2000] = 0
        #summing
        self.dat['dir_sum']       = np.nansum(dir_threshold,axis= (1,2))
        #normalising on I0
        self.dat['dir_norm']      = self.dat['dir_sum']/self.dat['Izero']
    
    def get_dir1D(self):  
        
        #load background from dark run and substract
        try:    
            #dir_bg        = np.nanmean(self.bg['dir'],axis=(0))
            raw_dir       = self.dat['dir'][np.logical_and(self.dat['timestamp_filter'],self.dat['count_mask']),:]#[count_mask,:,:]
            #dir_subbg     = raw_dir-dir_bg[np.newaxis,:]
            dir_bg = np.nanmean(raw_dir[:,self.rois['andor_dir_bg'][0]:self.rois['andor_dir_bg'][1]],axis=(1))
            dir_subbg = raw_dir[:,self.rois['andor_dir'][0]:self.rois['andor_dir'][1]]-dir_bg[:,np.newaxis]
            #thresholding
            dir_threshold = np.nansum(dir_subbg,axis=(1))
            #dir_threshold[dir_threshold<2000] = 0
            #summing
            self.dat['dir_sum']       = dir_threshold#np.nansum(dir_threshold,axis=1)
            #normalising on I0
            self.dat['dir_norm']      = self.dat['dir_sum']/self.dat['Izero']
        except:
            print('could not process dir')
    
    def get_inds_stepscans(self):
        #sort scan variable
        if self.acq=='ss':
            self.dat['bins'] = np.unique(self.dat['x_ss']) #print(np.unique(mono_enc_highrate_int.compute()))
            self.dat['inds'] = np.digitize(self.dat['x_ss'],self.dat['bins'])
        elif self.acq=='int':
            self.dat['bins'] = np.unique(self.dat['x'][self.dat['count_mask'][self.dat['timestamp_filter']]]) #print(np.unique(mono_enc_highrate_int.compute()))
            self.dat['inds'] = np.digitize(self.dat['x'][self.dat['count_mask'][self.dat['timestamp_filter']]],self.dat['bins'])
        self.dat['l']=len(self.dat['bins'].compute())
        self.dat['x_bin'] = da.array(self.dat['bins'].compute())
    
    def get_inds_flyscans(self,bintype='Nbins',binvar=80):
        
        if self.acq=='ss':
            x = self.dat['x_ss']
        elif self.acq=='int':
            x = self.dat['x'][self.dat['count_mask'][self.dat['timestamp_filter']]]
        
        if bintype == 'stepsize':
            try:
                step = binvar
                self.dat['bins'] = np.arange(np.min(x),np.max(x),step)
                self.dat['inds']=np.digitize(x,bin_edge)
                self.dat['l']=len(self.dat['bins'].compute())
                self.dat['x_bin'] = da.array(self.dat['bins'].compute())
            except:
                print('could not determine bins')
        elif bintype == 'Nbins':
            try:
                Nbin = binvar
                self.dat['bins'] = np.linspace(np.min(x),np.max(x),Nbin)
                self.dat['inds']=np.digitize(x,self.dat['bins'] )
                self.dat['l']=Nbin
                self.dat['x_bin'] = da.array(self.dat['bins'].compute())
            except:
                print('could not determine bins')

        else:
            print('binning type not defined')
            

    def binning(self):
        self.proc = {}
        dat = self.dat
        
        if 'x' in self.dat.keys():
            self.proc['x_bin']=self.dat['x_bin']
        
            l=self.dat['l']
            self.proc['apd_sort']=da.zeros(l)
            self.proc['apd_std']=da.zeros(l)
            self.proc['apd_on_sort']=da.zeros(l)
            self.proc['apd_on_std']=da.zeros(l)
            self.proc['apd_off_sort']=da.zeros(l)
            self.proc['apd_off_std']=da.zeros(l)
            
            self.proc['apd_sort_I0corr']=da.zeros(l)
            self.proc['apd_std_I0corr']=da.zeros(l)
            self.proc['apd_on_sort_I0corr']=da.zeros(l)
            self.proc['apd_on_std_I0corr']=da.zeros(l)
            self.proc['apd_off_sort_I0corr']=da.zeros(l)
            self.proc['apd_off_std_I0corr']=da.zeros(l)
            
            self.proc['Izero_sort']=da.zeros(l)
            self.proc['Izero_sort_std']=da.zeros(l)
            self.proc['Izero_sort_on']=da.zeros(l)
            self.proc['Izero_sort_on_std']=da.zeros(l)
            self.proc['Izero_sort_off']=da.zeros(l)
            self.proc['Izero_sort_off_std']=da.zeros(l)
            
    
            if self.acq == 'int':
                self.proc['RIXS_sort']=da.zeros((l,dat['vls_sum'].shape[1]))
                self.proc['RIXS_sort_std']=da.zeros((l,dat['vls_sum'].shape[1]))
                self.proc['RIXS_sort_on']=da.zeros((l,dat['vls_sum'].shape[1]))
                self.proc['RIXS_sort_on_std']=da.zeros((l,dat['vls_sum'].shape[1]))
                self.proc['RIXS_sort_off']=da.zeros((l,dat['vls_sum'].shape[1]))
                self.proc['RIXS_sort_off_std']=da.zeros((l,dat['vls_sum'].shape[1]))
                
                self.proc['SVLS_sort']=da.zeros((l,dat['svls_sum'].shape[1]))
                self.proc['SVLS_sort_std']=da.zeros((l,dat['svls_sum'].shape[1]))
                self.proc['SVLS_sort_on']=da.zeros((l,dat['svls_sum'].shape[1]))
                self.proc['SVLS_sort_on_std']=da.zeros((l,dat['svls_sum'].shape[1]))
                self.proc['SVLS_sort_off']=da.zeros((l,dat['svls_sum'].shape[1]))
                self.proc['SVLS_sort_off_std']=da.zeros((l,dat['svls_sum'].shape[1]))
                
                self.proc['DIR_sort']=da.zeros(l)
                self.proc['DIR_sort_std']=da.zeros(l)
                self.proc['DIR_sort_on']=da.zeros(l)
                self.proc['DIR_sort_on_std']=da.zeros(l)
                self.proc['DIR_sort_off']=da.zeros(l)
                self.proc['DIR_sort_off_std']=da.zeros(l)
    
                self.proc['DIRnorm_sort']=da.zeros(l)
                self.proc['DIRnorm_sort_std']=da.zeros(l)
                self.proc['DIRnorm_sort_on']=da.zeros(l)
                self.proc['DIRnorm_sort_on_std']=da.zeros(l)
                self.proc['DIRnorm_sort_off']=da.zeros(l)
                self.proc['DIRnorm_sort_off_std']=da.zeros(l)
            i=0
            for i in np.arange(l):
                try:
                    self.proc['apd_sort'][i] = da.array(da.squeeze(np.nanmean(dat['apd_sum'][((dat['inds'] == i).T&dat['I0_filter'])],axis=0)))
                    self.proc['apd_std'][i] = da.array(da.squeeze(np.nanstd(dat['apd_sum'][((dat['inds'] == i).T&dat['I0_filter'])],axis=0)))
    
                    #self.proc['apd_on_std'][i] = da.array(da.squeeze(np.nanstd(dat['apd_sum'][((dat['inds'] == i).T&dat['I0_filter']&dat['no_goose'])],axis=0)))
                    #self.proc['apd_off_sort'][i] = da.array(da.squeeze(np.nanmean(dat['apd_sum'][((dat['inds'] == i).T&dat['I0_filter']&dat['goose'])],axis=0)))
                    #self.proc['apd_off_std'][i] = da.array(da.squeeze(np.nanstd(dat['apd_sum'][((dat['inds'] == i).T&dat['I0_filter']&dat['goose'])],axis=0)))
              
                    self.proc['apd_sort_I0corr'][i] = da.array(da.squeeze(np.nanmean(dat['apd_I0corr'][((dat['inds'] == i).T&dat['I0_filter'])],axis=0)))
                    self.proc['apd_std_I0corr'][i] = da.array(da.squeeze(np.nanstd(dat['apd_I0corr'][((dat['inds'] == i).T&dat['I0_filter'])],axis=0)))
                    #self.proc['apd_on_sort_I0corr'][i] = da.array(da.squeeze(np.nanmean(dat['apd_I0corr'][((dat['inds'] == i).T&dat['I0_filter']&dat['no_goose'])],axis=0)))
                    #self.proc['apd_on_std_I0corr'][i] = da.array(da.squeeze(np.nanstd(dat['apd_I0corr'][((dat['inds'] == i).T&dat['I0_filter']&dat['no_goose'])],axis=0)))
                    #self.proc['apd_off_sort_I0corr'][i] = da.array(da.squeeze(np.nanmean(dat['apd_I0corr'][((dat['inds'] == i).T&dat['I0_filter']&dat['goose'])],axis=0)))
                    #self.proc['apd_off_std_I0corr'][i] = da.array(da.squeeze(np.nanstd(dat['apd_I0corr'][((dat['inds'] == i).T&dat['I0_filter']&dat['goose'])],axis=0)))
                except:
                    print('could not bin APD')
                try:
                    self.proc['Izero_sort'][i] = da.array(da.squeeze(np.nanmean(dat['Izero'][((dat['inds'] == i).T&dat['I0_filter'])],axis=0)))
                    self.proc['Izero_sort_std'][i] = da.array(da.squeeze(np.nanstd(dat['Izero'][((dat['inds'] == i).T&dat['I0_filter'])],axis=0)))
                    #self.proc['Izero_sort_on'][i] = da.array(da.squeeze(np.nanmean(dat['Izero'][((dat['inds'] == i).T&dat['I0_filter']&dat['no_goose'])],axis=0)))
                    #self.proc['Izero_sort_on_std'][i] = da.array(da.squeeze(np.nanstd(dat['Izero'][((dat['inds'] == i).T&dat['I0_filter']&dat['no_goose'])],axis=0)))
                    #self.proc['Izero_sort_off'][i] = da.array(da.squeeze(np.nanmean(dat['Izero'][((dat['inds'] == i).T&dat['I0_filter']&dat['goose'])],axis=0)))
                    #self.proc['Izero_sort_off_std'][i] = da.array(da.squeeze(np.nanstd(dat['Izero'][((dat['inds'] == i).T&dat['I0_filter']&dat['goose'])],axis=0)))
                except:
                    print('could not bin I0')
                    
                if self.acq == 'int':
                    try:
                        self.proc['RIXS_sort'][i,:] = da.array(da.squeeze(np.nanmean(dat['vls_sum'][((dat['inds'] == i).T&dat['I0_filter'])],axis=0)) )  
                        self.proc['RIXS_sort_std'][i,:] = da.array(da.squeeze(np.nanstd(dat['vls_sum'][((dat['inds'] == i).T&dat['I0_filter'])],axis=0)))
                        #self.proc['RIXS_sort_on'][i,:] = da.array(da.squeeze(np.nanmean(dat['vls_sum'][((dat['inds'] == i).T&dat['I0_filter']&dat['no_goose'])],axis=0)))
                        #self.proc['RIXS_sort_on_std'][i,:] = da.array(da.squeeze(np.nanstd(dat['vls_sum'][((dat['inds'] == i).T&dat['I0_filter']&dat['no_goose'])],axis=0)))
                        #self.proc['RIXS_sort_off'][i,:] = da.array(da.squeeze(np.nanmean(dat['vls_sum'][((dat['inds'] == i).T&dat['I0_filter']&dat['goose'])],axis=0)))
                        #self.proc['RIXS_sort_off_std'][i,:] = da.array(da.squeeze(np.nanstd(dat['vls_sum'][((dat['inds'] == i).T&dat['I0_filter']&dat['goose'])],axis=0)))
                    except:
                        ('could not save RIXS')
        
                    try: 
                        self.proc['SVLS_sort'][i,:] = da.array(da.squeeze(np.nanmean(dat['svls_sum'][((dat['inds'] == i).T&dat['I0_filter'])],axis=0))   )
                        self.proc['SVLS_sort_std'][i,:] = da.array(da.squeeze(np.nanstd(dat['svls_sum'][((dat['inds'] == i).T&dat['I0_filter'])],axis=0)))
                        #self.proc['SVLS_sort_on'][i,:] = da.array(da.squeeze(np.nanmean(dat['svls_sum'][((dat['inds'] == i).T&dat['I0_filter']&dat['no_goose'])],axis=0)))
                        #self.proc['SVLS_sort_on_std'][i,:] = da.array(da.squeeze(np.nanstd(dat['svls_sum'][((dat['inds'] == i).T&dat['I0_filter']&dat['no_goose'])],axis=0)))
                        #self.proc['SVLS_sort_off'][i,:] = da.array(da.squeeze(np.nanmean(dat['svls_sum'][((dat['inds'] == i).T&dat['I0_filter']&dat['goose'])],axis=0)))
                        #self.proc['SVLS_sort_off_std'][i,:] = da.array(da.squeeze(np.nanstd(dat['svls_sum'][((dat['inds'] == i).T&dat['I0_filter']&dat['goose'])],axis=0)))
                    except:
                        print('could not bin SVLS')
        #
                    try:
                        self.proc['DIR_sort'][i] = da.array(da.squeeze(np.nanmean(dat['dir_sum'][((dat['inds'] == i).T&dat['I0_filter'])],axis=0)))
                        self.proc['DIR_sort_std'][i] = da.array(da.squeeze(np.nanstd(dat['dir_sum'][((dat['inds'] == i).T&dat['I0_filter'])],axis=0)))
                        #self.proc['DIR_sort_on'][i] = da.array(da.squeeze(np.nanmean(dat['dir_sum'][((dat['inds'] == i).T&dat['I0_filter']&dat['no_goose'])],axis=0)))
                        #self.proc['DIR_sort_on_std'][i] = da.array(da.squeeze(np.nanstd(dat['dir_sum'][((dat['inds'] == i).T&dat['I0_filter']&dat['no_goose'])],axis=0)))
                        #self.proc['DIR_sort_off'][i] = da.array(da.squeeze(np.nanmean(dat['dir_sum'][((dat['inds'] == i).T&dat['I0_filter']&dat['goose'])],axis=0)))
                        #self.proc['DIR_sort_off_std'][i] = da.array(da.squeeze(np.nanstd(dat['dir_sum'][((dat['inds'] == i).T&dat['I0_filter']&dat['goose'])],axis=0)))
                                    
                        self.proc['DIRnorm_sort'][i] = da.array(da.squeeze(np.nanmean(dat['dir_norm'][((dat['inds'] == i).T&dat['I0_filter'])],axis=0)))
                        self.proc['DIRnorm_sort_std'][i] = da.array(da.squeeze(np.nanstd(dat['dir_norm'][((dat['inds'] == i).T&dat['I0_filter'])],axis=0)))
                        #self.proc['DIRnorm_sort_on'][i] = da.array(da.squeeze(np.nanmean(dat['dir_norm'][((dat['inds'] == i).T&dat['I0_filter']&dat['no_goose'])],axis=0)))
                        #self.proc['DIRnorm_sort_on_std'][i] = da.array(da.squeeze(np.nanstd(dat['dir_norm'][((dat['inds'] == i).T&dat['I0_filter']&dat['no_goose'])],axis=0)))
                        #self.proc['DIRnorm_sort_off'][i] = da.array(da.squeeze(np.nanmean(dat['dir_norm'][((dat['inds'] == i).T&dat['I0_filter']&dat['goose'])],axis=0)))
                        #self.proc['DIRnorm_sort_off_std'][i] = da.array(da.squeeze(np.nanstd(dat['dir_norm'][((dat['inds'] == i).T&dat['I0_filter']&dat['goose'])],axis=0)))
                    
                    except:
                        print('could not bin DIR')
                    
                i+=1
        else:   
            self.proc['x_bin']=[]
            self.proc['Izero_sort']=0
            self.proc['Izero_sort_std']=0
            self.proc['Izero_sort_on']=0
            self.proc['Izero_sort_on_std']=0
            self.proc['Izero_sort_off']=0
            self.proc['Izero_sort_off_std']=0
    
            self.proc['RIXS_sort']=da.zeros((dat['vls_sum'].shape[1]))
            self.proc['RIXS_sort_std']=da.zeros((dat['vls_sum'].shape[1]))
            self.proc['RIXS_sort_on']=da.zeros((dat['vls_sum'].shape[1]))
            self.proc['RIXS_sort_on_std']=da.zeros((dat['vls_sum'].shape[1]))
            self.proc['RIXS_sort_off']=da.zeros((dat['vls_sum'].shape[1]))
            self.proc['RIXS_sort_off_std']=da.zeros((dat['vls_sum'].shape[1]))
            
            self.proc['SVLS_sort']=da.zeros((dat['svls_sum'].shape[1]))
            self.proc['SVLS_sort_std']=da.zeros((dat['svls_sum'].shape[1]))
            self.proc['SVLS_sort_on']=da.zeros((dat['svls_sum'].shape[1]))
            self.proc['SVLS_sort_on_std']=da.zeros((dat['svls_sum'].shape[1]))
            self.proc['SVLS_sort_off']=da.zeros((dat['svls_sum'].shape[1]))
            self.proc['SVLS_sort_off_std']=da.zeros((dat['svls_sum'].shape[1]))
    
        
            try:        
                self.proc['Izero_sort'] = da.array(da.squeeze(np.nanmean(dat['Izero'][(dat['I0_filter'])])))
                self.proc['Izero_sort_std'] = da.array(da.squeeze(np.nanstd(dat['Izero'][(dat['I0_filter'])])))
                #self.proc['Izero_sort_on'] = da.array(da.squeeze(np.nanmean(dat['Izero'][(dat['I0_filter']&dat['no_goose'])])))
                #self.proc['Izero_sort_on_std'] = da.array(da.squeeze(np.nanstd(dat['Izero'][(dat['I0_filter']&dat['no_goose'])])))
                #self.proc['Izero_sort_off'] = da.array(da.squeeze(np.nanmean(dat['Izero'][(dat['I0_filter']&dat['goose'])])))
                #self.proc['Izero_sort_off_std'] = da.array(da.squeeze(np.nanstd(dat['Izero'][(dat['I0_filter']&dat['goose'])])))
            except:
                print('coudl not bin I0')

            try:
                self.proc['RIXS_sort'] = da.array(da.squeeze(np.nanmean(dat['vls_sum'][(dat['I0_filter'])],axis=0)) )  
                self.proc['RIXS_sort_std'] = da.array(da.squeeze(np.nanstd(dat['vls_sum'][(dat['I0_filter'])],axis=0)))
                #self.proc['RIXS_sort_on_std'] = da.array(da.squeeze(np.nanstd(dat['vls_sum'][(dat['I0_filter']&dat['no_goose'])],axis=0)))
                #self.proc['RIXS_sort_off'] = da.array(da.squeeze(np.nanmean(dat['vls_sum'][(dat['I0_filter']&dat['goose'])],axis=0)))
                #self.proc['RIXS_sort_off_std'] = da.array(da.squeeze(np.nanstd(dat['vls_sum'][(dat['I0_filter']&dat['goose'])],axis=0)))
            except:
                print('could not bin RIXS')

            try:
                self.proc['SVLS_sort'] = da.array(da.squeeze(np.nanmean(dat['svls_sum'][(dat['I0_filter'])],axis=0))  ) 
                self.proc['SVLS_sort_std'] = da.array(da.squeeze(np.nanstd(dat['svls_sum'][(dat['I0_filter'])],axis=0)))
                #self.proc['SVLS_sort_on'] = da.array(da.squeeze(np.nanmean(dat['svls_sum'][(dat['I0_filter']&dat['no_goose'])],axis=0)))
               # self.proc['SVLS_sort_on_std'] = da.array(da.squeeze(np.nanstd(dat['svls_sum'][(dat['I0_filter']&dat['no_goose'])],axis=0)))
                #self.proc['SVLS_sort_off'] = da.array(da.squeeze(np.nanmean(dat['svls_sum'][(dat['I0_filter']&dat['goose'])],axis=0)))
                #self.proc['SVLS_sort_off_std'] = da.array(da.squeeze(np.nanstd(dat['svls_sum'][(dat['I0_filter']&dat['goose'])],axis=0)))
            except:
                print('could not bin SVLS')

        
        print('binned data')
        '''    
            def save_reduced(self):
                output_fname = f'./proc/Run1{self.run}_{self.scantype}.h5'
                for key in self.proc.keys():
                    da.to_hdf5(output_fname, {f'/{key}': self.proc[key] })
                print('saved data')
        '''
    def save_reduced(self):
        output_fname = f'./proc/Run{self.run}_{self.scantype}.h5'
        if self.acq=='ss': 
            da.to_hdf5(output_fname, {   '/x':self.proc['x_bin'], 
                                         '/Izero_sort':self.proc['Izero_sort'], 
                                         '/Izero_sort_std':self.proc['Izero_sort_std'], 
                                         '/Izero_sort_on':self.proc['Izero_sort_on'], 
                                         '/Izero_sort_on_std':self.proc['Izero_sort_on_std'], 
                                         '/Izero_sort_off':self.proc['Izero_sort_off'], 
                                         '/Izero_sort_off_std':self.proc['Izero_sort_off_std'], 
                                         '/apd_sort':self.proc['apd_sort'], 
                                         '/apd_std':self.proc['apd_std'], 
                                         '/apd_on_sort':self.proc['apd_on_sort'], 
                                         '/apd_on_std':self.proc['apd_on_std'], 
                                         '/apd_off_sort':self.proc['apd_off_sort'], 
                                         '/apd_off_std':self.proc['apd_off_std'], 
                                         '/apd_sort_I0corr':self.proc['apd_sort_I0corr'], 
                                         '/apd_std_I0corr':self.proc['apd_std_I0corr'], 
                                         '/apd_on_sort_I0corr':self.proc['apd_on_sort_I0corr'], 
                                         '/apd_on_std_I0corr':self.proc['apd_on_std_I0corr'], 
                                         '/apd_off_sort_I0corr':self.proc['apd_off_sort_I0corr'], 
                                         '/apd_off_std_I0corr':self.proc['apd_off_std_I0corr']})  
        if self.acq=='int': 
            if 'x' in self.dat.keys():
                try:
                    da.to_hdf5(output_fname, {   '/x':self.proc['x_bin'], 
                                             '/apd_sort':self.proc['apd_sort'], 
                                             '/apd_std':self.proc['apd_std'], 
                                             '/apd_on_sort':self.proc['apd_on_sort'], 
                                             '/apd_on_std':self.proc['apd_on_std'], 
                                             '/apd_off_sort':self.proc['apd_off_sort'], 
                                             '/apd_off_std':self.proc['apd_off_std'], 
                                             '/apd_sort_I0corr':self.proc['apd_sort_I0corr'], 
                                             '/apd_std_I0corr':self.proc['apd_std_I0corr'], 
                                             '/apd_on_sort_I0corr':self.proc['apd_on_sort_I0corr'], 
                                             '/apd_on_std_I0corr':self.proc['apd_on_std_I0corr'], 
                                             '/apd_off_sort_I0corr':self.proc['apd_off_sort_I0corr'], 
                                             '/apd_off_std_I0corr':self.proc['apd_off_std_I0corr']})
                except:
                    print('could not save APDs')
                try:
                    da.to_hdf5(output_fname, {'/DIR_sort':self.proc['DIR_sort'], 
                                             '/DIR_sort_std':self.proc['DIR_sort_std'], 
                                             '/DIR_sort_on':self.proc['DIR_sort_on'], 
                                             '/DIR_sort_on_std':self.proc['DIR_sort_on_std'], 
                                             '/DIR_sort_off':self.proc['DIR_sort_off'], 
                                             '/DIR_sort_off_std':self.proc['DIR_sort_off_std'],
                                             '/DIRnorm_sort':self.proc['DIRnorm_sort'], 
                                             '/DIRnorm_sort_std':self.proc['DIRnorm_sort_std'], 
                                             '/DIRnorm_sort_on':self.proc['DIRnorm_sort_on'], 
                                             '/DIRnorm_sort_on_std':self.proc['DIRnorm_sort_on_std'], 
                                             '/DIRnorm_sort_off':self.proc['DIRnorm_sort_off'], 
                                             '/DIRnorm_sort_off_std':self.proc['DIRnorm_sort_off_std']})  
                except:
                    print('could not save andor_dir')
                
            try:
                da.to_hdf5(output_fname, {   '/Izero_sort':self.proc['Izero_sort'], 
                                             '/Izero_sort_std':self.proc['Izero_sort_std'], 
                                             '/Izero_sort_on':self.proc['Izero_sort_on'], 
                                             '/Izero_sort_on_std':self.proc['Izero_sort_on_std'], 
                                             '/Izero_sort_off':self.proc['Izero_sort_off'], 
                                             '/Izero_sort_off_std':self.proc['Izero_sort_off_std']})
            except:
                print('could not save I0')
            try:
                da.to_hdf5(output_fname, {   '/RIXS_sort':self.proc['RIXS_sort'], 
                                             '/RIXS_sort_std':self.proc['RIXS_sort_std'], 
                                             '/RIXS_sort_on':self.proc['RIXS_sort_on'], 
                                             '/RIXS_sort_on_std':self.proc['RIXS_sort_on_std'], 
                                             '/RIXS_sort_off':self.proc['RIXS_sort_off'], 
                                             '/RIXS_sort_off_std':self.proc['RIXS_sort_off_std']})  
            except:
                print('could not save VLS')
            try:
                da.to_hdf5(output_fname, {   
                                             '/SVLS_sort':self.proc['SVLS_sort'], 
                                             '/SVLS_sort_std':self.proc['SVLS_sort_std'], 
                                             '/SVLS_sort_on':self.proc['SVLS_sort_on'], 
                                             '/SVLS_sort_on_std':self.proc['SVLS_sort_on_std'], 
                                             '/SVLS_sort_off':self.proc['SVLS_sort_off'], 
                                             '/SVLS_sort_off_std':self.proc['SVLS_sort_off_std']})  
            except:
                print('could not save SVLS')

        print('saved data')
    def plot_run(self,norm):

        if 'x' in self.dat.keys():
            if self.acq=='int':
                y=np.arange(self.proc['RIXS_sort'].shape[1])
                fig,ax=plt.subplots(1,2)
          
                ax[0].pcolor(self.proc['x_bin'],y,self.proc['RIXS_sort_off'].T)
                ax[0].set_xlabel('inc. energy (eV)')
                ax[0].set_ylabel('emission (px)')
                ax[0].set_title('RIXS')
    
                ax[1].pcolor(self.proc['x_bin'],y,self.proc['RIXS_sort_on'].T)
                ax[1].set_xlabel('inc. energy (eV)')
                ax[1].set_ylabel('emission (px)')
                ax[1].set_title('RIXS')
            
            
            fig,ax=plt.subplots(1,2)
            if norm==True:
                ax[0].plot(self.proc['x_bin'],self.proc['apd_on_sort_I0corr'])
                ax[0].fill_between(self.proc['x_bin'],self.proc['apd_on_sort_I0corr']-self.proc['apd_on_std_I0corr'],self.proc['apd_on_sort_I0corr']+self.proc['apd_on_std_I0corr'],color='brown',alpha=0.5,label='± standard error')
                ax[0].set_xlabel('inc. energy (eV)')
                ax[0].set_ylabel('int. (arb. u.)')
                ax[0].set_title('norm. TFY')
                
                ax[1].plot(self.proc['x_bin'],self.proc['apd_off_sort_I0corr'])
                ax[1].fill_between(self.proc['x_bin'],self.proc['apd_off_sort_I0corr']-self.proc['apd_off_std_I0corr'],self.proc['apd_off_sort_I0corr']+self.proc['apd_off_std_I0corr'],color='brown',alpha=0.5,label='± standard error')
                ax[1].set_xlabel('inc. energy (eV)')
                ax[1].set_ylabel('int. (arb. u.)')
                ax[1].set_title('norm. TFY')
            if norm==False:
                ax[0].plot(self.proc['x_bin'],self.proc['apd_on_sort'])
                ax[0].fill_between(self.proc['x_bin'],self.proc['apd_on_sort']-self.proc['apd_on_std'],self.proc['apd_on_sort']+self.proc['apd_on_std'],color='brown',alpha=0.5,label='± standard error')
                ax[0].set_xlabel('inc. energy (eV)')
                ax[0].set_ylabel('int. (arb. u.)')
                ax[0].set_title('norm. TFY')
                
                ax[1].plot(self.proc['x_bin'],self.proc['apd_off_sort'])
                ax[1].fill_between(self.proc['x_bin'],self.proc['apd_off_sort']-self.proc['apd_off_sort_std'],self.proc['apd_off_sort']+self.proc['apd_off_sort_std'],color='brown',alpha=0.5,label='± standard error')
                ax[1].set_xlabel('inc. energy (eV)')
                ax[1].set_ylabel('int. (arb. u.)')
                ax[1].set_title('norm. TFY')

        else:
            y=np.arange(len(self.proc['RIXS_sort']))
            fig,ax=plt.subplots(1,1)
            ax.plot(y,self.proc['RIXS_sort'])
            ax.set_xlabel('emission (px)')
            ax.set_ylabel('intensity (arb. u.)')
        

def load_data(run, fh, chunks = 'auto', load_ttfex = True, evc_laser_on = 272,acq='int'):
    """
    loads the data

    from smalldata loads data into local variables...

    Parameters
    ----------
    run: string
         number of run to load

    Returns
    -------
    data:

    
    """
    int_detector_key = 'intg'
    keys = [('timing','eventcodes','evc_ss'),
            ('timing','destination','dest_ss'),
            ('det_rix_fim1','full_area','fim1_wf_ss'),
            ('det_rix_fim0','full_area','fim0_wf_ss'),
            ('det_crix_w8','full_area','apd_wf_ss'),
            ('det_rix_fim1','wfintegrate','fim1_sum_ss'),
            ('det_rix_fim0','wfintegrate','fim0_sum_ss'),
            ('det_crix_w8','wfintegrate','apd_sum_ss'),
            ('mono_hrencoder','value','mono_encoder_ss'),
           ]
    if load_ttfex:
        keys = keys + [('tt','ampl','amp_ss'),
            ('tt','fltpos','pos_ss'),
            ('tt','fltposfwhm','fwhm_ss'),
            ('c_piranha','full_area','pir_ss')]
    keys_int = [('intg','andor_dir','full_area','dir'),
            ('intg','andor_vls','full_area','vls'),
            ('intg','axis_svls','full_area','svls'),
            ('intg','andor_vls','timing_sum_eventcodes','evc_vls'),
            ('intg','axis_svls','timing_sum_eventcodes','evc_svls'),
            ('intg','andor_vls','timing_sum_timestamp','vls_timestamp'),#
            ('intg','axis_svls','timing_sum_timestamp','svls_timestamp'),
            ('intg' ,'andor_vls','det_rix_fim1_sum_full_area','fim1_wf_int'),
            ('intg' ,'andor_vls','det_rix_fim0_sum_full_area','fim0_wf_int'),
            ('intg' ,'andor_vls','hsd_sum_full_hsd_1__ROI_wf','hsd1_wf_int'),
            ('intg' ,'andor_vls','det_crix_w8_sum_full_area','apd_wf_int'),
            ('intg' ,'andor_vls','det_rix_fim1_sum_wfintegrate','fim1_sum_int'),
            ('intg' ,'andor_vls','det_rix_fim0_sum_wfintegrate','fim0_sum_int'),
            ('intg' ,'andor_vls','det_crix_w8_sum_wfintegrate','apd_sum_int'),
            ('intg' ,'andor_vls','mono_hrencoder_sum_value','mono_encoder_int'), 
            ('intg' ,'andor_vls','c_piranha_sum_full_area','pir_int'),
            ('intg' ,'andor_vls','timing_sum_eventcodes','evc_int'),
            ('intg' ,'andor_vls','timing_sum_destination','dest_int')
               ]
    #if load_ttfex:
    #    keys_int = keys_int +[(int_detector_key ,'unaligned_norm_tt_sum_fltpos','pos_int'),
    #        (int_detector_key ,'unaligned_norm_tt_sum_fltposfwhm','fwhm_int'),
    #        (int_detector_key ,'unaligned_norm_tt_sum_ampl','amp_int')
    #       ]
    
    data = {}
    data['timestamp'] = da.from_array(fh['timestamp'],chunks=chunks)
    if acq=='ss':
        # Load single shot keys
        for key in keys:
            try:
                data[key[2]] = da.from_array(fh[key[0]][key[1]], chunks=chunks) 
            except:
                print('missing key {0}'.format(key))

    # Normalize these parameters to the number of single shots per image
    try:
        data['count_int'] = da.from_array(fh[int_detector_key]['andor_vls']['count'],chunks=chunks)
    
        for key in keys_int:
            try:
                data[key[3]] = da.from_array(fh[key[0]][key[1]][key[2]], chunks=chunks)  
                print(data[key[3]].shape)
    
                if len(data[key[3]].shape)==1:
                    data[key[3]] = data[key[3]]/data['count_int']
        
                elif len(data[key[3]].shape)==2:
                    data[key[3]] = data[key[3]]/data['count_int'][:,np.newaxis]
                elif len(data[key[3]].shape)==3:
                    data[key[3]] = data[key[3]]/data['count_int'][:,np.newaxis,np.newaxis]
            except:
                print('missing key {0}'.format(key))
        
    except:
        print('missing  count - skipping integrated data')
    # Load scan variables  
    try:
        scan_key = list(fh['scan'].keys())[0]
        data['step_ss'] = da.from_array(fh['scan']['step_value'], chunks=chunks)
        data['x_ss'] = da.from_array(fh['scan'][scan_key], chunks=chunks)
        data['scan_variable'] = scan_key
    except:
        print('This run is not a step scan.')
        
    #Integrated step parameters also need to be normalized to counts.
    try:
        scan_key = list(fh['scan'].keys())[0]
        data['step'] = da.squeeze(da.from_array(fh[int_detector_key]['andor_vls']['scan_sum_step_value'], chunks=chunks))/data['count_int']
        data['x'] = da.squeeze(da.from_array(fh[int_detector_key]['andor_vls'][f'scan_sum_{scan_key}'], chunks=chunks))/data['count_int']
    except:
        print('Error loading integrated scan variables')

    if ('scan' not in fh.keys()):
        if (np.std(data['mono_encoder_int'])>100):
            # hr_fit = [-3.27866970e-03,  4.80124373e+02] ## Cobalt shift 2
            hr_fit = [-3.27082170e-03,  4.80858943e+02] ## Cobalt shift 3
            # hr_fit = [-1.04834283e-03,  1.05158194e+03]
            hr_energy = da.from_array(np.polyval(hr_fit,data['mono_encoder_int']))
            if 'scan' not in fh.keys():
                data['fly_scan'] = True
                data['x']=hr_energy
                data['scan_var_name'] = ['mono_ev']

    else:
        print('not a fly scan')
        data['fly_scan'] = False
        data['mono_encoder_int']=hr_energy


    # Generate a xray on and laser on 
    try:
        data['xray_on_int'] = data['dest_int']==4
        data['laser_on_int'] = data['evc_int'][:,evc_laser_on]>0.5
        data['dest_int'] = data['dest_int']
    except:
        print('no laser code for int variable')

    data['xray_on_ss'] = data['dest_ss']==4
    data['laser_on_ss'] = data['evc_ss'][:,evc_laser_on]>0.5
    data['dest_ss'] = data['dest_ss']

    return data




def avg_TFY(exp,runs,acq,exp_c,run_dark):
        
    data=chemRIXSdat(exp='rixl1043623', run=runs[0],run_dark=run_dark,acq=acq,exp_c=exp_c)
    data.init_data()
    dat={}
    Izero_sort = []
    Izero_sort_std = []
    Izero_sort_off = []
    Izero_sort_off_std = []
    Izero_sort_on = []
    Izero_sort_on_std = []
    apd_off_sort = []
    apd_off_sort_I0corr = []
    apd_off_std = []
    apd_off_std_I0corr = []
    apd_on_sort = []
    apd_on_sort_I0corr = []
    apd_on_std_I0corr = []
    apd_sort = []
    apd_sort_I0corr = []
    apd_std = []
    apd_std_I0corr = []
    x = []
    
    for run in runs:
        fname = f'./proc/Run{run}_{data.scantype}.h5'
        fh = h5py.File(fname, 'r')
        Izero_sort.append(fh["Izero_sort"])
        Izero_sort_std.append(fh["Izero_sort_std"])
        Izero_sort_off.append(fh["Izero_sort_off"])
        Izero_sort_off_std.append(fh["Izero_sort_off_std"])
        Izero_sort_on.append(fh["Izero_sort_on"])
        Izero_sort_on_std.append(fh["Izero_sort_on_std"])
        apd_off_sort.append(fh["apd_off_sort"])
        apd_off_sort_I0corr.append(fh["apd_off_sort_I0corr"])
        apd_off_std.append(fh["apd_off_std"])
        apd_off_std_I0corr.append(fh["apd_off_std_I0corr"])
        apd_on_sort.append(fh["apd_on_sort"])
        apd_on_sort_I0corr.append(fh["apd_on_sort_I0corr"])
        apd_on_std_I0corr.append(fh["apd_on_std_I0corr"])
        apd_sort.append(fh["apd_sort"])
        apd_sort_I0corr.append(fh["apd_sort_I0corr"])
        apd_std.append(fh["apd_std"])
        apd_std_I0corr.append(fh["apd_std_I0corr"])
        x.append(fh["x"])
        if data.scantype=='int':
            RIXS_off_sort.append(fh["RIXS_sort_off"])
            RIXS_off_std.append(fh["RIXS_sort_off_std"])
            RIXS_on_sort.append(fh["RIXS_sort_on"])
            RIXS_on_sort.append(fh["RIXS_sort_on_std"])
            RIXS_sort.append(fh["RIXS_sort"])
            RIXS_std.append(fh["RIXS_sort_std"])
            
            DIR_off_sort.append(fh["DIR_sort_off"])
            DIR_off_std.append(fh["DIR_sort_off_std"])
            DIR_on_sort.append(fh["DIR_sort_on"])
            DIR_on_sort.append(fh["DIR_sort_on_std"])
            DIR_sort.append(fh["DIR_sort"])
            DIR_std.append(fh["DIR_sort_std"])

    
    
    Izero_sort = np.asarray(Izero_sort)
    Izero_sort_std = np.asarray(Izero_sort_std)
    Izero_sort_off = np.asarray(Izero_sort_off)
    Izero_sort_off_std = np.asarray(Izero_sort_off_std)
    Izero_sort_on = np.asarray(Izero_sort_on)
    Izero_sort_on_std = np.asarray(Izero_sort_on_std)
    apd_off_sort = np.asarray(apd_off_sort)
    apd_off_sort_I0corr = np.asarray(apd_off_sort_I0corr)
    apd_off_std = np.asarray(apd_off_std)
    apd_off_std_I0corr = np.asarray(apd_off_std_I0corr)
    apd_on_sort = np.asarray(apd_on_sort)
    apd_on_sort_I0corr = np.asarray(apd_on_sort_I0corr)
    apd_on_std_I0corr = np.asarray(apd_on_std_I0corr)
    apd_sort = np.asarray(apd_sort)
    apd_sort_I0corr = np.asarray(apd_sort_I0corr)
    apd_std = np.asarray(apd_std)
    apd_std_I0corr = np.asarray(apd_std_I0corr)  
    x = np.asarray(x)  
    if data.scantype=='int':
        RIXS_sort = np.asarray(RIXS_sort)
        RIXS_sort_std = np.asarray(RIXS_sort_std)
        RIXS_sort_off = np.asarray(RIXS_sort_off)
        RIXS_sort_off_std = np.asarray(RIXS_sort_off_std)
        RIXS_sort_on = np.asarray(RIXS_sort_on)
        RIXS_sort_on_std = np.asarray(RIXS_sort_on_std)    
        DIR_sort = np.asarray(DIR_sort)
        DIR_sort_std = np.asarray(DIR_sort_std)
        DIR_sort_off = np.asarray(DIR_sort_off)
        DIR_sort_off_std = np.asarray(DIR_sort_off_std)
        DIR_sort_on = np.asarray(DIR_sort_on)
        DIR_sort_on_std = np.asarray(DIR_sort_on_std)
        
    
    dat['Izero_sort_avg'] = np.nanmean(Izero_sort,axis=0)
    dat['Izero_sort_std_avg'] = np.nanmean(Izero_sort_std,axis=0)
    dat['Izero_sort_off_avg'] = np.nanmean(Izero_sort_off,axis=0)
    dat['Izero_sort_off_std_avg'] = np.nanmean(Izero_sort_off_std,axis=0)
    dat['Izero_sort_on_avg'] = np.nanmean(Izero_sort_on,axis=0)
    dat['Izero_sort_on_std_avg'] = np.nanmean(Izero_sort_on_std,axis=0)
    dat['apd_off_sort_avg'] = np.nanmean(apd_off_sort,axis=0)
    dat['apd_off_sort_I0corr_avg'] = np.nanmean(apd_off_sort_I0corr,axis=0)
    dat['apd_off_std_avg'] = np.nanmean(apd_off_std,axis=0)
    dat['apd_off_std_I0corr_avg'] = np.nanmean(apd_off_std_I0corr,axis=0)
    dat['apd_on_sort_avg'] = np.nanmean(apd_on_sort,axis=0)
    dat['apd_on_sort_I0corr_avg'] = np.nanmean(apd_on_sort_I0corr,axis=0)
    dat['apd_on_std_I0corr_avg'] = np.nanmean(apd_on_std_I0corr,axis=0)
    dat['apd_sort_avg'] = np.nanmean(apd_sort,axis=0)
    dat['apd_sort_I0corr_avg'] = np.nanmean(apd_sort_I0corr,axis=0)
    dat['apd_std_avg'] = np.nanmean(apd_std,axis=0)
    dat['apd_std_I0corr_avg'] = np.nanmean(apd_std_I0corr,axis=0)
    dat['x_avg'] = np.nanmean(x,axis=0)
    
    if data.scantype=='int':
        dat['RIXS_sort_avg'] = np.nanmean(RIXS_sort,axis=0)
        dat['RIXS_sort_std_avg'] = np.nanmean(RIXS_sort_std,axis=0)
        dat['RIXS_sort_off_avg'] = np.nanmean(RIXS_sort_off,axis=0)
        dat['RIXS_sort_off_std_avg'] = np.nanmean(RIXS_sort_off_std,axis=0)
        dat['RIXS_sort_on_avg'] = np.nanmean(RIXS_sort_on,axis=0)
        dat['RIXS_sort_on_std_avg'] = np.nanmean(RIXS_sort_on_std,axis=0)
        dat['DIR_sort_avg'] = np.nanmean(DIR_sort,axis=0)
        dat['DIR_sort_std_avg'] = np.nanmean(DIR_sort_std,axis=0)
        dat['DIR_sort_off_avg'] = np.nanmean(DIR_sort_off,axis=0)
        dat['DIR_sort_off_std_avg'] = np.nanmean(DIR_sort_off_std,axis=0)
        dat['DIR_sort_on_avg'] = np.nanmean(DIR_sort_on,axis=0)
        dat['DIR_sort_on_std_avg'] = np.nanmean(DIR_sort_on_std,axis=0)

    return dat

def load_ROIS():
    #valid for last shift

    # Define ROIs for APDs and FIMs - double check at least once per shift with '/old/Check_Waveform.ipynb'
    rois={}
    channels={}
    rois['apd0_wf'] = [50,200]
    rois['apd7_wf'] = [65,84]
    rois['apd6_wf'] = None
    rois['apd5_wf'] = [72,87]
    rois['apd4_wf'] = None
    rois['apd_wf_BG'] = [0,40]
    
    rois['fim0_roi'] = [100,114]
    rois['fim1_roi'] = [120,131]
    rois['fim0_bg'] =[0, 80]
    rois['fim1_bg'] = [0, 80]
    
    #generally the APD waveform for goosed and ungoosed shots is different. Not applicable in this experiment for the integrating detectors
    rois['apd_wf_goose'] = [70,77]   
    rois['apd_wf_nogoose'] = [75,80]
    
    #which channels were useful during this experiment - can also be checked with '/old/Check_Waveform.ipynb'
    channels['apd_wf'] = [5,6,7]
    channels['fim1'] = [6]
    channels['fim0'] = [6]

    
    rois['vls_bg2D'] = [[300,-1],[20,100]]
    rois['vls_bg1D'] = [[300,-1],[20,100]]

    
    rois['andor_dir'] = [0,2048]
    rois['andor_dir_bg'] = [40,60]
    rois['svls'] = [2000,6000]

    #######
    # vls_offset_roi = [20,100,330,510] # Nitrogen
    rois['vls_bg1D'] = [1400,1600] # Cobalt
    rois['vls_bg1D'] = [700,760] # Cobalt
    rois['vls_bg2D'] = [20,100,400,510] # Oxygen
    ########
    
    return rois,channels


def calc_IZero(fim0, fim1, rois,channels):
    fim0_sum = sum_FIM_wfs(fim0, rois['fim0_roi'], rois['fim0_bg'],channels['fim0'])
    fim1_sum = sum_FIM_wfs(fim1, rois['fim1_roi'], rois['fim1_bg'],channels['fim1'])
    return fim0_sum+fim1_sum


def sum_FIM_wfs(fim, rois,rois_bg,channels):
    fim_subset = fim[:, channels, :]
    fim_bkg = fim_subset[:, :, rois_bg[0]:rois_bg[1]].mean(axis=2)
    fim_bkg_expanded = fim_bkg[:, :, None]
    fim_bkg_expanded = da.broadcast_to(fim_bkg[:,:,None],(fim_bkg.shape[0],len(channels),256))
    fim_corr = fim_subset - fim_bkg_expanded
    return da.abs(fim_corr[:,:,rois[0]:rois[1]]).sum(axis=(1, 2))


def sum_apd(apds,rois,channels):
    
    apd_bkg = apds[:, :, rois['apd_wf_BG'][0]:rois['apd_wf_BG'][1]].mean(axis=2)
    apd_bkg_expanded = apd_bkg[:, :, None]
    apd_bkg_expanded = da.broadcast_to(apd_bkg[:,:,None],(apd_bkg.shape[0],8,256))
    apd_bgf = apds - apd_bkg_expanded
    apd_sum = np.zeros(apds.shape[0])
    i=0
    
    if (rois['apd4_wf'] is not None) & (4 in channels['apd_wf']):
        apd_sum = apd_sum + np.sum(np.abs(apd_bgf[:,4,rois['apd4_wf'][0]:rois['apd4_wf'][1]]),axis=1)
        i=i+1
    if (rois['apd5_wf'] is not None) & (5 in channels['apd_wf']):
        apd_sum = apd_sum + np.sum(np.abs(apd_bgf[:,5,rois['apd5_wf'][0]:rois['apd5_wf'][1]]),axis=1)
        i=i+1
    if (rois['apd6_wf'] is not None) & (6 in channels['apd_wf']):
        apd_sum = apd_sum + np.sum(np.abs(apd_bgf[:,6,rois['apd6_wf'][0]:rois['apd6_wf'][1]]),axis=1)
        i=i+1
    if (rois['apd7_wf'] is not None) & (7 in channels['apd_wf']):
        apd_sum = apd_sum + np.sum(np.abs(apd_bgf[:,7,rois['apd7_wf'][0]:rois['apd7_wf'][1]]),axis=1)
        i=i+1
    return apd_sum
