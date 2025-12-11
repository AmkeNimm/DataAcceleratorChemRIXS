from pathlib import Path

import h5py
import numpy as np
import pytest
import shutil
import yaml

from chemrixs.smalldata import SmallData
from test_smalldata import get_test_file


def test_integrating_exists():
    fname, fyaml = get_test_file()
    data = SmallData(fname,fyaml)

    assert hasattr(data,'integrating')
