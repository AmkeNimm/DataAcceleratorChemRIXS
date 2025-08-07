

"""Utilities for working with HDF5 files."""

from functools import cached_property
from pathlib import Path

import h5py
import yaml
from singleshot import Singleshot
from integrating import Integrating
import contextlib

class SmallData:
    """
    A  class for fast read-only interface to our small data files.

    This class is just a really thin wrapper over our HDF5 files that makes it easier
    to read in parts of the data at a time. This makes it much faster to perform
    small tasks where simple metadata is required, rather than reading in the whole
    header.

    All data is available as attributes, through ``__getattr__`` magic. Thus,
    accessing eg. `xx`` will go and get the xx directly from the
    file, and store them in memory.

    Anything that is read in is stored in memory so the second access is much faster.
    However, the memory can be released simply by deleting the attribute (it can be
    accessed again, and the data will be re-read).

    Parameters
    ----------
    path : str or Path
        The filename to read from.

    Notes
    -----
    To check if a particular attribute is available, use ``hasattr(obj, attr)``.
    Many attributes will not show up dynamically in an interpreter, because they are
    gotten dynamically from the file.
    """
    '''
    First level keys
    ['Sums', 'UserDataCfg', 'c_piranha', 'crix_w8', 'det_crix_w8', 'det_rix_fim0', 'det_rix_fim1', 'epics_archiver', 'intg', 'lightStatus', 'mono_hrencoder', 'rix_fim0', 'rix_fim1', 'scan', 'timestamp', 'timing']

    Problem : THEY WILL CHANGE
    '''


    
    def __init__(self, path: str | Path | h5py.File | h5py.Group):
        self.__file = None

        self.path = Path(path.filename).resolve()
        self.__file= path
        try:
            with open('roi_input.yml', 'r') as file:
                 self.rois = yaml.safe_load(file)
        except:
            print('ROIs not defined - or check filename') 
            self.rois = {}
        #self.scanvar = self.runinfo

     
    def is_open(self) -> bool:
        """Whether the file is open."""
        return bool(self.__file)

    def __del__(self):
        """Close the file when the object is deleted."""
        if self.__file:
            self.__file.close()

    def close(self):
        """Close the file."""
        self.__intgrp = None
        self.__ssgrp = None

        # need to refresh these
        with contextlib.suppress(AttributeError):
            del self.__ssgrp

        with contextlib.suppress(AttributeError):
            del self.__intgrp

        if self.__file:
            self.__file.close()
        self.__file = None

    def open(self):  # noqa: A003
        """Open the file."""
        if not self.__file:
            self.__file = h5py.File(self.path, "r")
            self.__intgrp = self.__file["/intg"]
            self.__ssgrp = self.__file["/"]

    @cached_property
    def runinfo(self):

        if not self.__file:
            self.open()
        print(self.__file.keys())
        try:
            if 'scan' in self.__file.keys():
                if 'mono_ev' in self.__file['/scan'].keys():
                    scanvar = 'mono'
                elif 'mono_ev' in self.__file['/scan'].keys():
                    scanvar = 'delay'
            else:
                scanvar='static'
                print('did not record scan variable. If this should be a delay or mono scan the scanvars may have changed')
        except:
            print('trouble determining scan variable')
        
        '''
        need to find a way to distinguish between fly and step scans here, maybe it's also okay to do that later
        '''

        return scanvar

    @cached_property
    def integrating(self) -> h5py.Group:
        """Get the integrated detector group."""
        print('accessing intgrp')
        if not self.__file:
            self.open()
        return Integrating(self.__intgrp)
    
    @cached_property
    def singleshot(self) -> h5py.Group:
        """Get the single shot data."""
        print('accessing SSdat')
        if not self.__file:
            self.open()
        return Singleshot(self.__ssgrp)
       



def process_apds(raw_apd,rois):

    return self.apds

def process_I0(raw_fim0,raw_fim1,rois):
    
    return self.I0


