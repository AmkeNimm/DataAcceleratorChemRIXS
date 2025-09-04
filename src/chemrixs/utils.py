import h5py
import numpy as np


#TODO: is this for loop the most efficient way - probably yes, since ROIs 
# may be channel dependent ; confirm channel numbers match
def sumchan_helper(raw_fims,rois):
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
def sum_channels(obj, channel_dict,fyaml): #dict includes {fim0: fim_0,....}
   
    rois = fyaml
    
    for key in channel_dict: 
        #if we are parsing from the integrating class this is an array
        if hasattr(getattr(obj,key), "__len__"):
            summed = sumchan_helper(getattr(obj,key), rois[channel_dict[key]]) 
            setattr(obj, channel_dict[key], summed)
        #if we are parsing from the singleshot class this is an object
        
        #FIXME: implement option for getting channels from preproc or full area
        else:
            summed = sumchan_helper(getattr(getattr(obj,key),'preproc'),rois[channel_dict[key]]) 
            setattr(obj, channel_dict[key], summed)