from functools import cached_property
from pathlib import Path

import h5py
import yaml
import contextlib
from chemrixs.utils import *
from chemrixs.smalldata import SmallData


class ProcessData():
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

    def __init__(self, path: str | Path | h5py.File | h5py.Group, bgpath: Path):
        
        self.data = SmallData(path)

        #load BG data or process it from smalldata and save
        if bgpath.exists():
            #load BG
            self.bg =  h5py.File(self.bgpath, "r")
        else:
            self.bg = SmallData(bgpath)

            #process BG

        

    def process_ss(self):
        
        return 

    def process_int(self):
    
        return
    
    def check_rois(self):
        fig,ax=plt.subplots(1,1)
        

