import time
import h5py

import numpy as np
import matplotlib.pyplot as plt
import sys
import scipy.stats as st

from chemrixs.average import Average
from chemrixs.smalldata import SmallData
from chemrixs.process import Reduced
from chemrixs.utils import *
from pathlib import Path

base_folder =  '/sdf/data/lcls/ds/rix/'
proc_folder = './proc/'

bgrun = 61
runs=[66]

exp = 'rix101331225'


fyaml = '../roi_input.yml'

bgname = f'{base_folder}/{exp}/hdf5/smalldata/{exp}_Run{bgrun:04d}.h5'
bgyaml = '../BGroi_input.yml'

run = runs[0]

fname = f'{base_folder}/{exp}/hdf5/smalldata/{exp}_Run{run:04d}.h5'
fname = f'{base_folder}/{exp}/hdf5/smalldata/{exp}_Run{run:04d}.h5'
bgname = f'{base_folder}/{exp}/hdf5/smalldata/{exp}_Run{bgrun:04d}.h5'
fyaml = '../roi_inputTT.yml'
bgyaml = '../BGroi_input.yml'

data = SmallData(fname,fyaml)
# bg = SmallData(bgname, bgyaml)

expected_count = st.mode(data.integrating.axis_svls.count, keepdims=False)[0]

data.integrating.axis_svls.piranha.shape
# data.integrating.axis_svls.eventcodes.shape[:,272]
mask_on = np.asarray([data.integrating.axis_svls.eventcodes[:,data.yaml['evc'][True]]/expected_count>0.5]).squeeze()
mask_off = np.asarray([data.integrating.axis_svls.eventcodes[:,data.yaml['evc'][False]]/expected_count>0.5]).squeeze()
piranha_on = data.integrating.axis_svls.piranha[mask_on,:]
piranha_off = data.integrating.axis_svls.piranha[mask_off,:]

print('got data')

ROI=[1100,1600]
# u,s,v=np.linalg.svd((piranha_off[1:,:])[:2000,:])

v, s = decomp_((piranha_off[1:,:])[:,:],2000) #decomposition of BG data (dark)
traces = decomp_1d(v,s,data.integrating.axis_svls.piranha[:,:],ROI,neigs=3) #all data only ROI

print('svd bg subtraction done')

px = np.arange(ROI[0],ROI[1])
x = px
spectra = traces[mask_on[:]]

spectra.shape == (traces[mask_on[:]].shape[0], traces[mask_on[:]].shape[1])
x.shape == (traces[mask_on[:]].shape[0],)
params = np.array([
    gaussian_moments_linear(x, spectra[i])
    for i in range(spectra.shape[0])
])
lb = np.array([0.0,   1200,  10,   0.9, -1])  # A, mu, sigma, C (lower)
ub = np.array([0.3,   1400, 40,  1.1, 0])    
params_fit = np.array([
    fit_gaussian_fast_linear(x, spectra[i],lb,ub)
    for i in range(spectra.shape[0])
])

print('fit done')
A     = params[:, 0]
mu    = params[:, 1]
sigma = params[:, 2]
A_fit     = params_fit[:, 0]
mu_fit    = params_fit[:, 1]
sigma_fit = params_fit[:, 2]

leading_edge  = mu - sigma
leading_edge_fit  = mu_fit - sigma_fit

np.savetxt(f"proc/leading_edge{run}.txt", leading_edge)

np.savetxt(f"proc/leading_edge_fit{run}.txt", leading_edge_fit)