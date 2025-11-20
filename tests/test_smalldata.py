
import numpy as np
from chemrixs.smalldata import SmallData
import yaml
import shutil
import pytest

@pytest.fixture
def get_test_file():
    fname='/sdf/home/a/amke/DataAcceleratorChemRIXS/tests/testfile_Run0000.h5'
    fyaml='/sdf/home/a/amke/DataAcceleratorChemRIXS/tests/roi_input.yml'

    yield fname, fyaml    


def test_smalldata_hasdatfor_svls_vls_andordir(get_test_file):
    fname, fyaml = get_test_file
    data = SmallData(fname,fyaml)
    with open(fyaml,'r') as file:
        conf=yaml.safe_load(file)
        det_list = conf['int_detectors']
        epics_list = conf['epics']['attr']

    # getattr(data,'integrating')
    assert hasattr(data,'integrating')
    for det in det_list:
        assert hasattr(data.integrating,det)

    for epics in epics_list:
        assert epics in data.epics

@pytest.mark.parametrize('file_str', ['testfile.h5','testfile_Run0.h5'])
def test_smalldata_errors(tmp_path, file_str,get_test_file):
    #test errors here
    fname_org, fyaml = get_test_file
    fname = tmp_path /file_str
    shutil.copy(fname_org,fname)
    with pytest.raises(ValueError,match='Given h5 file has no defined run number'):
        data = SmallData(fname,fyaml)