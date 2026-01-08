from pathlib import Path

import h5py
import numpy as np
import pytest
import shutil
import yaml

from chemrixs.smalldata import SmallData
from test_smalldata import get_test_file


def test_integrating_exists():
    fname, fyaml = get_test_file(type = 'svls_only', yamltype='SVLS_andordir_only')
    data =     SmallData(fname,fyaml)
    with pytest.raises(KeyError,match='andor_dir is not in this file'):
        hasattr(data,'integrating')

def test_accessing_axissvls():
    fname, fyaml = get_test_file()
    data = SmallData(fname,fyaml)
    with pytest.raises(AttributeError,match="'Integrating' object has no attribute 'fu'"):
        data.integrating.fu
    

def test_accessing_andordir():
    fname, fyaml = get_test_file()
    data = SmallData(fname,fyaml)

def test_accessing_piranha_dir():
    fname, fyaml = get_test_file()
    data = SmallData(fname,fyaml)

def test_count():
    '''OSError                                   Traceback (most recent call last)
    File ~/DataAcceleratorChemRIXS/src/chemrixs/integrating.py:139, in Integrating.countmask(self)
        138 try:
    --> 139     expected_count = st.mode(det.count, keepdims=False)[0]
        140 except:
    '''
#Problem occuring when BG and data are not both (not) dropletised

    return

        