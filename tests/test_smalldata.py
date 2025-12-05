
import numpy as np
from chemrixs.smalldata import SmallData
import yaml
import shutil
import pytest
from pathlib import Path
import h5py

@pytest.fixture
def get_test_file():
    fname='/sdf/home/a/amke/DataAcceleratorChemRIXS/tests/testfile_Run0000.h5'
    fyaml='/sdf/home/a/amke/DataAcceleratorChemRIXS/tests/test_roi_input.yml'

    yield fname, fyaml    


def test_smalldata_hasdatfor_svls_vls_andordir(get_test_file):
    fname, fyaml = get_test_file
    data1 = SmallData(fname,fyaml)
    with h5py.File(fname,'r') as fh5:
        data2 =SmallData(fh5,fyaml)
    fPath = Path(fname)
    data3 = SmallData(fPath,fyaml)
    
    for data in [data1,data2,data3]:
        with open(fyaml,'r') as file:
            conf=yaml.safe_load(file)
            det_list = conf['int_detectors']
            epics_list = conf['epics']['attr']

        getattr(data,'integrating')
        assert hasattr(data,'integrating')
        for det in det_list:
            assert hasattr(data.integrating,det)

        for epics in epics_list:
            assert epics in data.epics

        assert data.is_open()

@pytest.mark.parametrize('file_str', ['testfile.h5','testfile_Run0.h5'])
def test_smalldata_filename_error(tmp_path, file_str,get_test_file):
    #test errors here
    fname_org, fyaml = get_test_file
    fname = tmp_path /file_str
    shutil.copy(fname_org,fname)
    with pytest.raises(ValueError,match='Given h5 file has no defined run number'):
        data = SmallData(fname,fyaml)

@pytest.mark.parametrize('file_str', ['testfile.yaml'])
def test_smalldata_yamlerrors(tmp_path, file_str,get_test_file):
    fname, fyaml_org = get_test_file
    fyaml = tmp_path /file_str
    with pytest.raises(FileNotFoundError,match='Config yaml file not found - check filename'):
        data = SmallData(fname,fyaml)

def test_closeSmalldata(get_test_file):
    fname, fyaml = get_test_file
    data = SmallData(fname,fyaml)
    closed_attr = ['_SmallData__intgrp','_SmallData__ssgrp']

    data.__exit__()
    for attr in closed_attr:
        assert not hasattr(data, attr)
    assert data._SmallData__file is None

    data.__enter__()
    for attr in closed_attr:
        assert hasattr(data, attr)
    assert data._SmallData__file is not None

@pytest.mark.parametrize('file_str', ['delay_scan_testfile_Run0000.h5','mono_scan_testfile_Run0000.h5','mono_fly_testfile_Run0000.h5'])
def test_runinfo(tmp_path, file_str,get_test_file):
    fname_org, fyaml = get_test_file
    fname = tmp_path /file_str # this is now a path object
    shutil.copy(fname_org,fname)
    data = SmallData(fname,fyaml)
    assert hasattr(data,'runinfo')

    print(data.runinfo)
    if 'delay_scan' in file_str:
        print(file_str)
        data = SmallData(fname,fyaml)
        assert data.scantype=='delay'
        data = SmallData(fname,fyaml,'delay')
    if 'mono_scan' in file_str:
        data = SmallData(fname,fyaml,'mono')
    if 'delay_fly' in file_str:
        data = SmallData(fname,fyaml,'delay_fly')
    if 'mono_fly' in file_str:
        data = SmallData(fname,fyaml,'mono_fly')
    assert hasattr(data,'runinfo')


