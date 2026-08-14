# DataAcceleratorChemRIXS

## What this is
chemrixs is a Python data-reduction package for the chemRIXS endstation on the RIX beamline at LCLS (SLAC's X-ray free-electron laser). It processes "smalldata" HDF5 files produced by psana into background-subtracted, normalized, binned spectra (PFY, HERFD, CIE, CET, RIXS maps), with pump-probe (laser on/off) support. Author: Amke Nimmrich (UW), maintained with Bryna Hazelton.

## Get Started
setup enviroment defined in 'conf.yml':

install miniconda: https://www.anaconda.com/docs/getting-started/miniconda/install#linux-2

# install miniconda first
conda env create -f conf.yml     # creates env "dachemrixs"
conda env update -f conf.yml     # after editing conf.yml — restart terminal to pick it up

conf.yml pulls from conda-forge and lcls-i and installs: dask, h5py, ipympl, jupyter, matplotlib, numpy, psana, psutil, pytest, pytest-cov, python>=3.11, pyyaml, scipy, sphinx.
pyproject.toml separately defines the installable package itself (pip install . from the repo root, src-layout under src/chemrixs), with a lighter runtime dependency set (dask[complete], h5py>=3.7, ipympl, jupyter, matplotlib, numpy>=1.23, psutil, scipy>=1.9) plus an optional doc extra (sphinx). Note psana — the LCLS DAQ/analysis library — is only in conf.yml, not pyproject.toml; you need the conda env (or an LCLS/S3DF login) to actually pull raw data, but downstream processing of already-exported smalldata HDF5 files should work from the pip package alone.

To do analysis several 'pre steps' are needed:

## Calibration
see notebook xx

## Timing Tool Analysis
see notebook './jupyter_notebook/TT_test.ipynb'

From there several runs can easily be run in a few steps as seen in notebook  xx.
All parameters for reduction are defined in xx.yaml

## Run reduction and plot data
examples in './jupyter_notebook'
