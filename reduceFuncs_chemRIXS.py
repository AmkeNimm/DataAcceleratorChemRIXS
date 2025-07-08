import time
import h5py
import numpy as np
import matplotlib.pyplot as plt
cmap = plt.cm.get_cmap('terrain').reversed()
import scipy.stats as st
from scipy.optimize import curve_fit
import dask.array as da
import dask.dataframe as dd
import psutil
#from distributed import LocalCluster, Client #local on S3DF
#from dask_jobqueue.slurm import SLURMCluster #local on S3DF
import os
import sys
from scipy.stats import binned_statistic
from scipy import ndimage

class chemRIXSdat:
    """
    initialises the chemRIXSdat class 
    
    Providing basic information on experiment

    Parameters
    ----------
    exp: string
            experiment number, e.g. 'rix100836924'
    run: int
            run number of run to analyse, e.g. 24
    run_dark: int
            run number of a run which was recorded without laser and X-ray for background subtraction
    acq: {'int', 'ss'}
            acquistion type to be analysed - either integrating detectors ('int') or single shot ('ss')
    exp_c: int
            count of shots per integrated frame
    
    Returns
    -------
    self: class
            class containing raw and processed data
        
    """

    def __init__(self, exp, run,run_dark, acq,exp_c):


        
        self.exp = exp
        self.run = run
        self.run_dark = run_dark
        self.acq = acq
        self.exp_c = exp_c                              
        self.base_folder = '/sdf/data/lcls/ds/rix/'     #chemRIXS directory on S3DF



    def init_data(self, dask=True):
        """
        loads the data into chemRIXSdat class
    
        uses 'load_data' function to load data from smalldata into local variables and 
        'load_ROIs' to load regions of interest for different detectors

        Parameters:
        -----------
        dask: bool, default: True
                should data be loaded as dask array (True) or numpy array (False)
        
        Returns
        -------
        self.dat: 
                containing raw data
        self.bg: 
                containing data from dark run for background subtraction
        self.rois:
                containing ROIs for different detectors - both for background and areas containing data
            
        """
        #
        fname = f'{self.base_folder}/{self.exp}/hdf5/smalldata/{exp}_Run{self.run:04d}.h5'
        fh = h5py.File(fname, 'r')

        darkname = f'{self.base_folder}/{self.exp}/hdf5/smalldata/{exp}_Run{self.run_dark:04d}.h5'
        fh_dark = h5py.File(darkname, 'r')
        
        self.bg = load_data(self.run_dark, fh_dark, chunks = 'auto', load_ttfex = True, evc_laser_on = 272,acq=self.acq)
        self.dat = load_data(self.run, fh, chunks = 'auto', load_ttfex = True, evc_laser_on = 272,acq=self.acq)

        
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
