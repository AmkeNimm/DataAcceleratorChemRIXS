
import h5py
import matplotlib.pyplot as plt
import numpy as np
import os

from functools import cached_property
from pathlib import Path
from chemrixs.utils import *
from chemrixs.process import Reduced

class Average():
    """
    A class to average over several runs. 

    Takes runnumber as input, if these runs have been processed before
    they will simply be averaged, otherwise the 'Reduced' class is called 
    to process these runs first.

    Parameters
    ----------
    runs : list
        containing the integers of the runs to average

    proc_path : str or Path
        The filename structure and location of the processed runs. 
        Should be complete by simply adding the '{run:04d}.h5'

    avg : str
        String determining the way of averaging: 

    output_path : str or Path
        The filename for the output of averaged data.
    
    
    raw_path : str or Path
        The filename structure for the data to analyse.
        Should be complete by simply adding the '{run:04d}.h5'

    bgpath : str or Path
        The filename for a darkscan that can be used for background subtraction.

    fyaml : str or Path
        yaml file with settings for processing of unprocessed runs.

    bgyaml : str or Path
        yaml file with settings for processing the BG data, needed for unprocessed runs.

    save : bool
        Boolean determining if the processed data should be saved where processing necessary.

    scantype : str
        Optional, determining the type of scan for processing. If not given, this will be
        determined by the data structure.

    norm : bool
        Boolean determining if data should be normalised by I0 or not when processing.
        
    """

    def __init__(self, runs: list | int, proc_path: str | Path, avg: str, output_path: str | Path,
                raw_path: str | Path, bgpath: str | Path, fyaml: str | Path, bgyaml: str | Path, 
                save: bool = True, scantype: str = '',norm: bool = True):
        
        self.runs = runs
        self.proc_path = proc_path
        self.avg = avg
        self.output_path = output_path

        if len(raw_path) is not None:
            self.raw_path = raw_path
            self.bgpath = bgpath
            self.fyaml = fyaml
            self.bgyaml = bgyaml
            self.scantype = scantype
            self.norm = norm

        self.check_reduce()
        self.average


    def check_reduce(self):
        for run in self.runs:
            proc_path = self.proc_path + f'{run:04d}.h5'
            if os.path.isfile(proc_path) == False:
                fname = self.raw_path + f'{run:04d}.h5'
                tmp = Reduced(fname,self.bgpath,self.fyaml,self.bgyaml, 
                        save=True,scantype=self.scantype,norm=self.norm)
                self.scantype = tmp.data.scantype

        
        return
    
    @cached_property
    def average(self):
        print(self.proc_path)
        avg = avg_data(self.runs, self.proc_path)

        return avg

    def plot_svls2D(self, calibrated=False,savefig=False,transparent=True,figsize=(12,8),scale=1):
        if calibrated == True:
            emi = emi
        else:
            emi = np.arange(self.average['axis_svls_off_mean'].shape[1])

        ddatmax = np.nanmax(self.average['axis_svls_on_mean'].T-self.average['axis_svls_off_mean'].T)
 
        fig,ax = plt.subplots(1,3,sharex=True, sharey=True,figsize=figsize)
        ax[0].pcolor(self.average['scanvar_on'],emi,np.flip(self.average['axis_svls_off_mean'],axis=1).T,cmap = 'Reds',
                     vmin=0,vmax=np.nanmax(self.average['axis_svls_off_mean'])/scale)
        ax[1].pcolor(self.average['scanvar_on'],emi,np.flip(self.average['axis_svls_on_mean'],axis=1).T,cmap = 'Reds',
                     vmin=0,vmax=np.nanmax(self.average['axis_svls_on_mean'])/scale)
        ax[2].pcolor(self.average['scanvar_on'],emi,np.flip(self.average['axis_svls_on_mean'],axis=1).T-np.flip(self.average['axis_svls_off_mean'],axis=1).T,cmap = 'bwr',
                     vmin=-ddatmax,vmax=ddatmax)

        ax[0].set_xlabel('inc. energy (eV)')
        ax[1].set_xlabel('inc. energy (eV)')
        ax[2].set_xlabel('inc. energy (eV)')

        ax[0].set_ylabel('emission (pixel)')

        ax[0].set_title('laser off')
        ax[1].set_title('laser on')
        ax[2].set_title('difference')

        ax[0].set_xlim([np.nanmin(self.average['scanvar_on']),np.nanmax(self.average['scanvar_on'])])

        if savefig:
            fig.savefig(f'figs/SVLS2D_{self.runs[0]}_{self.runs[-1]}.png',transparent=transparent,
                        dpi=200, bbox_inches='tight')

        return fig

    def plot_svls1D(self,savefig=False,transparent=True,figsize=(12,8)):
        """
        Plotting binned and averaged SVLS detector, collapsed on scanvar axis.
        
        :param self: Description
        """
        
        fig,ax = plt.subplots(1,3,sharex=True, sharey=True,figsize=figsize)
        ax[0].plot(self.average['scanvar_off'],np.nanmean(self.average['axis_svls_off_mean'],axis=1))
        ax[1].plot(self.average['scanvar_on'],np.nanmean(self.average['axis_svls_on_mean'],axis=1))
        ax[2].plot(self.average['scanvar_on'],np.nanmean(self.average['axis_svls_on_mean']-self.average['axis_svls_off_mean'],axis=1))
        if self.scantype=='mono_fly':
            ax[0].set_xlabel('inc. energy (eV)')
            ax[1].set_xlabel('inc. energy (eV)')
            ax[2].set_xlabel('inc. energy (eV)')
        elif self.scantype=='delay_fly':
            ax[0].set_xlabel('delay (s)')
            ax[1].set_xlabel('delay (s)')
            ax[2].set_xlabel('delay (s)')
        ax[0].set_xlim([np.nanmin(self.average['scanvar_on']),np.nanmax(self.average['scanvar_on'])])
        
    


    
