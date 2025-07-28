
from functools import cached_property
from pathlib import Path

import h5py
import numpy as np
import yaml
from loadDat import *


class Singleshot():

    def __init__(self, ssgrp: h5py.Group):
        self.grp = ssgrp