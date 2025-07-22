

"""Utilities for working with HDF5 files."""

from functools import cached_property
from pathlib import Path

import h5py
import numpy as np



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
        self.__ssgrp = self.__file["/"]
        self.__intgrp = self.__file["/intg"]

     
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
        self.__ssdat = None

        # need to refresh these
        with contextlib.suppress(AttributeError):
            del self.__ssdat

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
            self.__ssdat = self.__file["/"]


    @property
    def intgrp(self) -> h5py.Group:
        """Get the integrated detector group."""
        print('accessing intgrp')
        if not self.__file:
            self.open()
        return Integrating(self.__intgrp)
    
    def ssgrp(self) -> h5py.Group:
        """Get the single shot data."""
        ssdat = {}
        if not self.file:
            self.open()
        self.ssdat = Singelshot(self.__ssgrp)

    
class Integrating():

    def __init__(self, intgrp: h5py.Group):
        print('initialising Integrating')
        grp = intgrp
        self.andor_dir = Detector(grp["andor_dir"], ['crix_w8_sum_ptrigCount','det_crix_w8_sum_full_area'])
        print(f'{self.andor_dir}')

class Singleshot():

    def __init__(self, ssgrp: h5py.Group):
        self.grp = ssgrp

        '''for name in self._ssdat_attrs:
            if name in self.file:
                print(name)
                ssdat[name] = self.file[name]
        '''


class Detector():

    def __init__(self, group: h5py.Group, data_to_read: list[str]):
        print('initialising detector')
        #group = first level grou, e.g. andordir, data_to_read: lower level data in andor_dir
        self.grp = group
        #self.prop_factory(data_to_read)
        
    '''
        def prop_set(self, data_set):
            print(f'geting {data_set}')
            print(f'geting {self.grp[data_set]}')
            return self.grp[data_set]


        def prop_factory(self, data_to_read: list[str]): #function that makes funtions
            print('setting up properties')
            for dataset in data_to_read:          
        #        setattr(self.__class__, dataset, cached_property(self.prop_set(dataset)))
                prop=cached_property(self.prop_set(dataset))
                setattr(self.__class__, dataset,prop)
                prop.__set_name__(self.__class__, dataset)
    '''

    @cached_property
    def get_crixw8(self):
        return self.grp['crix_w8_sum_ptrigCount']
    
    
    @cached_property
    def get_crixw8(self):
        return self.grp['crix_w8_sum_ptrigCount']
