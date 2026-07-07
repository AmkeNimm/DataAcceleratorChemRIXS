# DataAcceleratorChemRIXS

## Get Started
setup enviroment defined in 'conf.yml':

install miniconda: https://www.anaconda.com/docs/getting-started/miniconda/install#linux-2

conda env create -f xyz.yaml #create conda environment with all packages needed for  
conda env update -f xyz.yaml #update environment after changes in yaml file - you may need to restart terminal for this to kick in

To do analysis several 'pre steps' are needed:

## Calibration
see notebook xx

## Timing Tool Analysis
see notebook './jupyter_notebook/TT_test.ipynb'

From there several runs can easily be run in a few steps as seen in notebook  xx.
All parameters for reduction are defined in xx.yaml

## Run reduction and plot data
examples in './jupyter_notebook'
