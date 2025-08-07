from functools import cached_property
from pathlib import Path

import h5py
import numpy as np

class Detector():

    def __init__(self, group: h5py.Group, data_to_read: dict):
        print(f'initialising {group}')
        #group = first level grou, e.g. andordir, data_to_read: lower level data in andor_dir
        self.grp = group
        self.prop_factory(data_to_read)
        
    def prop_set(self, data_set):
        def fget(self):
            return self.grp[data_set][()]
        return fget


    def prop_factory(self, data_to_read: dict): #function that makes funtions
        print('setting up properties')
        for name, dataset in data_to_read.items():          
            prop=cached_property(self.prop_set(dataset))
            setattr(self.__class__, name, prop)
            prop.__set_name__(self.__class__, name)


    def process(self):
        '''
        Overall function to process incoming data, this includes filtering 
        on I0 and mismatches in data
        
        Parameters
        ----------
        rois : dictionary
            Containing ROIs for different detectors.
        

        Notes
        -----
        To check if a particular attribute is available, use ``hasattr(obj, attr)``.
        Many attributes will not show up dynamically in an interpreter, because they are
        gotten dynamically from the file.
        
        '''

        self.apds = process_apds(self.apd,self.rois)
        self.I0 = process_I0()

    

    def subtract_bg(self, run_bg):

        return self.bgf
    
class daskDetector():

    def __init__(self, group: h5py.Group, data_to_read: dict):
        print(f'initialising {group}')
        #group = first level grou, e.g. andordir, data_to_read: lower level data in andor_dir
        self.grp = group
        self.prop_factory(data_to_read)
        
    def prop_set(self, data_set):
        def fget(self):
            return self.grp[data_set][()]
        return fget


    def prop_factory(self, data_to_read: dict): #function that makes funtions
        print('setting up properties')
        for name, dataset in data_to_read.items():          
            prop=cached_property(self.prop_set(dataset))
            setattr(self.__class__, name, prop)
            prop.__set_name__(self.__class__, name)


    def process(self):
        '''
        Overall function to process incoming data, this includes filtering 
        on I0 and mismatches in data
        
        Parameters
        ----------
        rois : dictionary
            Containing ROIs for different detectors.
        

        Notes
        -----
        To check if a particular attribute is available, use ``hasattr(obj, attr)``.
        Many attributes will not show up dynamically in an interpreter, because they are
        gotten dynamically from the file.
        
        '''

        self.apds = process_apds(self.apd,self.rois)
        self.I0 = process_I0()

    

    def subtract_bg(self, run_bg):

        return self.bgf