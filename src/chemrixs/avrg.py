
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
                Reduced(fname,self.bgpath,self.fyaml,self.bgyaml, 
                        save=True,scantype=self.scantype,norm=self.norm)
        
        return
    
    @cached_property
    def average(self):
        print(self.proc_path)
        avg = avg_data(self.runs, self.proc_path)

        return avg

    def plot_2D(self):

        fig,ax = plt.subplots(1,3)
        ax[0].pcolor(self.average['axis_svls_off_mean'])
        ax[1].pcolor(self.average['axis_svls_on_mean'])
        ax[2].pcolor(self.average['axis_svls_on_mean']-self.average['axis_svls_on_mean'])

        return fig

    def plot_1D(self):
        fig,ax =plt.subplots(1,1)
        ax.plot()
    


    
