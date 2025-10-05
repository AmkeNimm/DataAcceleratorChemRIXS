

"""Utilities for working with HDF5 files."""

from functools import cached_property
from pathlib import Path

import h5py
import yaml
from chemrixs.singleshot import Singleshot
from chemrixs.integrating import Integrating
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

    Attributes
    ----------
    is_open:

    __del__:

    close:

    __exit__:

    __enter__:

    open:

    runinfo:

    integrating:

    singleshot:



    Notes
    -----
    To check if a particular attribute is available, use ``hasattr(obj, attr)``.
    Many attributes will not show up dynamically in an interpreter, because they are
    gotten dynamically from the file.

    TODO: add more error messages for potential failures
    """

    def __init__(self, path: str | Path | h5py.File | h5py.Group, fyaml: str | Path, scantype: str = ''):
        self.__file = None
        self.run = int(path[-7:-3])
        self.scantype = scantype
        # self.path = Path(path.filename).resolve()
        # #FIXME: should I keep thsi self.__file?
        # self.__file= path

        ########

        if isinstance(path, h5py.File):
            self.path = Path(path.filename).resolve()
            self.__file = path
        elif isinstance(path, h5py.Group):
            self.path = Path(path.file.filename).resolve()
            self.__file = path.file
        elif isinstance(path, str | Path):
            self.path = Path(path).resolve()
            #self.___File is not assigned here, cause the input is not an h5 file or group,
            # so we are only loading it in self.open()

        ########



        try:
            with open(fyaml, 'r') as file:
                 self.yaml = yaml.safe_load(file)
        except FileNotFoundError as fe: 
            raise FileNotFoundError('Config yaml file not found - check filename') from fe

     
    def is_open(self) -> bool:
        """
        Function to check whether the file is open.
        """
        return bool(self.__file)

    def __del__(self):
        """
        Function to close the file when the object is deleted.
        """
        if self.__file:
            self.__file.close()

    def close(self):
        """
        Function to close the file.
        """
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

    def __exit__(self,*exc):
        self.close()

    def __enter__(self):
        self.open()
        return self


    def open(self):  
        #FIXME: need to add option for h5 file or str or path as input
        """
        Open the file.
        """
        if not self.__file:
            self.__file = h5py.File(self.path, "r")
            self.__intgrp = self.__file["/intg"]
            self.__ssgrp = self.__file["/"]
        if not hasattr(self, '_SmallData__intgrp'):
            self.__intgrp = self.__file["/intg"]
        

    #FIXME: Unclear what the keys are now to identify scans...
    @cached_property
    def runinfo(self):
        """
        Function to determine the type of run that is being analysed.


        """
        if not self.__file:
            self.open()
        print(self.__file.keys())

        if len(self.scantype) > 1:
            scantype = self.scantype
        
        else:
            #FIXME: all possible scan types, x/y scane, power titrations, ...
            try:
                if 'scan' in self.__file.keys():
                    if self.yaml['scanvar']['mono'] in self.__file['/scan'].keys():
                        scantype = 'mono'
                    elif self.yaml['scanvar']['delay'] in self.__file['/scan'].keys():
                        scantype = 'delay'
                    elif self.yaml['scanvar']['waveplate'] in self.__file['/scan'].keys():
                        scantype = 'power'
                else:
                    #FIXME: mono_encoder linked to specific detector
                    if (np.std(self.integrating.andor_vls.mono_encoder)>500)&self.yaml['scanvar']['mono'] not in self.__file['/scan'].keys():
                        scantype = 'mono_fly'
                    elif self.yaml['scanvar']['delay_fly'] in self.__file['/scan'].keys():
                        scantype = 'delay_fly'
                    scantype='static'
                    print('did not record scan variable. If this should be a delay or mono scan the scanvars may have changed')
            except:
                print('trouble determining scan variable')
                scantype = ''
        print(f'scantype is {scantype}')

        """
        need to find a way to distinguish between fly and step scans here, maybe it's also okay to do that later
        """

        return scantype

    @cached_property
    def integrating(self) -> h5py.Group:
        """
        Function to get the integrated detector group and load data into attribute.
        """
        print('accessing intgrp')
        if not self.__file:
            self.open()
        return Integrating(self.__intgrp, self.yaml,self.epics,self.scantype)
    
    @cached_property
    def singleshot(self) -> h5py.Group:
        """
        Function to get the single shot detector group and load data into attribute.
        """
        print('accessing SSdat')
        if not self.__file:
            self.open()
        return Singleshot(self.__ssgrp, self.yaml)
    
    @cached_property
    def epics(self):
        """
        """
        print('accessing epics')
        if not self.__file:
            self.open()
        epics = {}
        for key in self.yaml['epics']['attr'].keys():
            epics[key] = self.__file[f"/{self.yaml['epics']['key']}/{self.yaml['epics']['attr'][key]}"][:,1]
        return epics
       


