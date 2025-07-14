

"""Utilities for working with HDF5 files."""

from functools import cached_property
from pathlib import Path

import h5py
import numpy as np



class HDF5Handling:
    """
    A base class for fast read-only interface to our HDF5 file metadata.

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


    
    _defaults = {}
    _string_attrs = frozenset({"xx"})
    _int_attrs = frozenset({"xx"})
    _float_attrs = frozenset({})
    _bool_attrs = frozenset({})

    def __init__(self, path: str | Path | h5py.File | h5py.Group):
        self.__file = None

        if isinstance(path, h5py.File):
            self.path = Path(path.filename).resolve()
            self.__file = path
            self.__intg = path["/intg"]
            self.__singles = path["/Data"]
        elif isinstance(path, h5py.Group):
            self.path = Path(path.file.filename).resolve()
            self.__file = path.file
            self.__header = path
            self.__datagrp = self.__file["/Data"]
        elif isinstance(path, str | Path):
            self.path = Path(path).resolve()




