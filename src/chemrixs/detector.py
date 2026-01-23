from functools import cached_property
from pathlib import Path
import dask.array as da
import dask.dataframe as dd
import h5py
import numpy as np
from chemrixs.utils import *
import yaml

class Detector():
# TODO: create cases for when we only want to load parts of specific detectors via indexing, 
# this will need user input
    def __init__(self, group: h5py.Group, data_to_read: dict, useDask: bool, chunks:int):
        """
            A  class to load data from a specific detector.

            This class takes input which variables should be loaded for detector object, if they
            should be loaded as dask array and if not with which chunk size. The dask option will lead
            to speed up for larger arrays - chunk size may have to be adjusted.
            TODO: advice on how to choose chunk size

            All detector keys are available as attributes, through ``__getattr__`` magic. 

            Parameters
            ----------
            group : h5py.Group
                The h5 group containing data for this specific detector.
            data_to_read : dict
                Dictionary of name for data that should be loaded and the corresponding key in the h5 file. 
                This way the variables can be saved under more intuitive names than in the h5 file.
            useDask : bool
                If data should be loaded as dask array or not. Most likely dask arrays will mainly be used 
                for the single shot data.
            chunks : int
                Defining the chunk size for loading dask arrays. These should be optimised for ideal speed up
                of data processing.

            Notes
            -----
            To check if a particular attribute is available, use ``hasattr(obj, attr)``.
            Many attributes will not show up dynamically in an interpreter, because they are
            gotten dynamically from the file.
        """

        #group = first level grou, e.g. andordir, data_to_read: lower level data in andor_dir
        self.grp = group
        self.prop_factory(data_to_read, useDask, chunks)
        
        
    def prop_set(self, data_set, useDask,chunks): #function that loads data from h5 group
        """
        Function that loads data from the h5 group.

        Data is loaded through the fget function since the attribute needs to be a function.
        
        Parameters
        ----------
        data_set : str
            Key for h5 file
        use_Dask : bool
            If data should be loaded as dask array or not. Most likely dask arrays will mainly be used 
            for the single shot data.
        chunks : int
            Defining the chunk size for loading dask arrays. These should be optimised for ideal speed up
            of data processing.
        
        """
        def fget(self):
            if useDask:
                dat = da.from_array(self.grp[data_set], chunks = chunks)
                return dat
            return self.grp[data_set][()]
        return fget


    def prop_factory(self, data_to_read: dict, useDask: bool, chunks: int): #function that makes data cached properties
        """
        Function that attaches loaded data as cached property.

        The cached property makes sure the data is only loaded when actually called. Once it is called,
        it stays in memory so it does not need to be loaded again.
        Data is loaded through the fget function since the attribute needs to be a function.
        
        Parameters
        ----------
        data_to_read : dict
                Dictionary of name for data that should be loaded and the corresponding key in the h5 file. 
                This way the variables can be saved under more intuitive names than in the h5 file.
        useDask : bool
            If data should be loaded as dask array or not. Most likely dask arrays will mainly be used 
            for the single shot data.
        chunks : int
            Defining the chunk size for loading dask arrays. These should be optimised for ideal speed up
            of data processing.
        
        """
        print('setting up properties')
        for name, dataset in data_to_read.items():    
            prop=cached_property(self.prop_set(dataset, useDask,chunks))
            setattr(self.__class__, name, prop)
            prop.__set_name__(self.__class__, name)

