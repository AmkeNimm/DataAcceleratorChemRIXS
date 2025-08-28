import h5py
import numpy as np


#TODO: is this for loop the most efficient way - probably yes, since ROIs 
# may be channel dependent ; confirm channel numbers match
def sum_channels(raw_fims,rois):
    if raw_fims.ndim == 3:    
        bg = np.mean(raw_fims[...,rois['bg_roi'][0]:rois['bg_roi'][1]],axis= -1)
        bgf = raw_fims - bg[...,np.newaxis]
        fim_sum = np.zeros([bgf.shape[0],len(rois['channels'])])
        print(bgf.shape)
        i=0
        for c in rois['channels']:
            fim_sum[:,i] = np.nansum(np.abs(bgf[:,c-1,rois['roi'][i][0]:rois['roi'][i][1]]),axis = 1)
            i=i+1
        fimsum =np.nansum(fim_sum, axis=1)
    
    elif raw_fims.ndim == 2:
        fimsum = np.zeros([raw_fims.shape[0]])
        for c in rois['channels']:
            fimsum = fimsum + (raw_fims[:,c-1]).squeeze()
    
    elif raw_fims.ndim==1:
        fimsum = raw_fims

    return fimsum