import numpy as np

def sumchan_helper(raw_fims,rois):
    '''
    Function. that does the actual summing of fim and crix channels

    Parameters
    ----------
    raw_fims : array
        containing the actual data, either pre-processed or raw - these cases will be distinguished below

    rois : array
        describing the area containing background and the region of interest, 
        as well as the channels that should be used for reduction.
        Defined in the config yaml file.

    '''
    if raw_fims.ndim == 3:    
        bg = np.mean(raw_fims[...,rois['bg_roi'][0]:rois['bg_roi'][1]],axis= -1)
        bgf = raw_fims - bg[...,np.newaxis]
        fim_sum = np.zeros([bgf.shape[0],len(rois['channels'])])
        # print(bgf.shape)
        i=0
        #TODO: is this for loop the most efficient way - probably yes, since ROIs 
        # may be channel dependent ; confirm channel numbers match
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

def sum_channels(obj,fyaml): #dict includes {fim0: fim_0,....}
    '''
    Function to handle singleshot or integrating fims and crix 
    
    Different cases depending if object from singleshot or array from 
    integrating detectors is being parsed

    Parameters
    ----------
    obj : object
        object containing fim or crixs data
    channel_dict : dictionary
        dict containing list of which detectors to process, 
        and how the attribute should be called
    fymal : dictionary
        Dict from yml file that contains information of ROIs for the different detectors
    '''
    rois = fyaml
    channel_dict = fyaml['channels_to_integrate']
    
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

def normalise(dat, I0):
    #FIXME: not sure if I need to implement different cases for when dimensions are in a different order
    if dat.ndim == 1:
        norm = dat/I0
    elif dat.ndim == 2:
        norm = dat/I0[:,np.newaxis]
    elif dat.ndim == 3:
        norm = dat/I0[:,np.newaxis,np.newaxis]
    else:
        raise ValueError('Dimension don not match for normalising detector')
    return norm


def bin_data(data,bin_axis,bin_with='scan_var',normalize=True):
    #FIXME: do I call this function for each detector somewhere else, or do I loop through the detectors here
    # for now writing this for an individual detector

     binned_data = {}


     return binned_data


    # def bin_detector(processed_data,detector,binning_info,normalize):
    # binned_detector = {}
    # variable = binning_info[0]
    # var_unique = binning_info[1]
    # inds = binning_info[2]

    # if processed_data['laser_any'].all() == False:
    #     laser = np.ones(processed_data['laser_any'].shape[0],'bool')
    #     if 'off' not in binned_detector.keys():
    #         binned_detector['off'] = {}
    
    #     if processed_data[detector].ndim == 1:
    #         binned_detector['off']['sum'] = np.zeros(var_unique.shape[0])
    #         binned_detector['off']['mean'] = np.zeros(var_unique.shape[0])
    #         binned_detector['off']['std'] = np.zeros(var_unique.shape[0])
            
    #     if processed_data[detector].ndim == 2:
    #         binned_detector['off']['sum'] = np.zeros([var_unique.shape[0],processed_data[detector].shape[1]])
    #         binned_detector['off']['mean'] = np.zeros([var_unique.shape[0],processed_data[detector].shape[1]])
    #         binned_detector['off']['std'] = np.zeros([var_unique.shape[0],processed_data[detector].shape[1]])
        
    #     for i in range(0, len(var_unique)):
    #         if normalize == True:
    #             if processed_data[detector].ndim == 1:
    #                 binned_detector['off']['sum'][i] = np.array(np.nansum((processed_data[detector]/processed_data['I0_int_sum'])[(laser)&(inds == i+1)],0))
    #                 binned_detector['off']['mean'][i] = np.array(np.nanmean((processed_data[detector]/processed_data['I0_int_sum'])[(laser)&(inds == i+1)],0))
    #                 binned_detector['off']['std'][i] = np.array(np.nanstd((processed_data[detector]/processed_data['I0_int_sum'])[(laser)&(inds == i+1)],0))


    #             if processed_data[detector].ndim == 2:
    #                 binned_detector['off']['sum'][i] = np.array(np.nansum((processed_data[detector]/processed_data['I0_int_sum'][:,np.newaxis])[(laser)&(inds == i+1)],0))
    #                 binned_detector['off']['mean'][i] = np.array(np.nanmean((processed_data[detector]/processed_data['I0_int_sum'][:,np.newaxis])[(laser)&(inds == i+1)],0))
    #                 binned_detector['off']['std'][i] = np.array(np.nanstd((processed_data[detector]/processed_data['I0_int_sum'][:,np.newaxis])[(laser)&(inds == i+1)],0))


    #         else:
    #             binned_detector['off']['sum'][i] = np.array(np.nansum(processed_data[detector][(laser)&(inds == i+1)],0))
    #             binned_detector['off']['mean'][i] = np.array(np.nanmean(processed_data[detector][(laser)&(inds == i+1)],0))
    #             binned_detector['off']['std'][i] = np.array(np.nanstd(processed_data[detector][(laser)&(inds == i+1)],0))

    
    # else:
    #     if 'off' not in binned_detector.keys():
    #         binned_detector['off'] = {}
    #         binned_detector['on'] = {}
    #     laser_on = processed_data['laser_on']
    #     laser_off = processed_data['laser_off']

    #     if processed_data[detector].ndim == 1:
    #         binned_detector['on']['sum'] = np.zeros(var_unique.shape[0])
    #         binned_detector['on']['mean'] = np.zeros(var_unique.shape[0])
    #         binned_detector['on']['std'] = np.zeros(var_unique.shape[0])
    #         binned_detector['off']['sum'] = np.zeros(var_unique.shape[0])
    #         binned_detector['off']['mean'] = np.zeros(var_unique.shape[0])
    #         binned_detector['off']['std'] = np.zeros(var_unique.shape[0])

            
    #     if processed_data[detector].ndim == 2:
    #         binned_detector['on']['sum'] = np.zeros([var_unique.shape[0],processed_data[detector].shape[1]])
    #         binned_detector['on']['mean'] = np.zeros([var_unique.shape[0],processed_data[detector].shape[1]])
    #         binned_detector['on']['std'] = np.zeros([var_unique.shape[0],processed_data[detector].shape[1]])
    #         binned_detector['off']['sum'] = np.zeros([var_unique.shape[0],processed_data[detector].shape[1]])
    #         binned_detector['off']['mean'] = np.zeros([var_unique.shape[0],processed_data[detector].shape[1]])
    #         binned_detector['off']['std'] = np.zeros([var_unique.shape[0],processed_data[detector].shape[1]])

        
    #     for i in range(0, len(var_unique)):

    #         if normalize == True:
    #             if processed_data[detector].ndim == 1:

    #                 binned_detector['on']['sum'][i] = np.array(np.nansum((processed_data[detector]/processed_data['I0_int_sum'])[(laser_on)&(inds == i+1)],0))
    #                 binned_detector['on']['mean'][i] = np.array(np.nanmean((processed_data[detector]/processed_data['I0_int_sum'])[(laser_on)&(inds == i+1)],0))
    #                 binned_detector['on']['std'][i] = np.array(np.nanstd((processed_data[detector]/processed_data['I0_int_sum'])[(laser_on)&(inds == i+1)],0))
                    
    #                 binned_detector['off']['sum'][i] = np.array(np.nansum((processed_data[detector]/processed_data['I0_int_sum'])[(laser_off)&(inds == i+1)],0))
    #                 binned_detector['off']['mean'][i] = np.array(np.nanmean((processed_data[detector]/processed_data['I0_int_sum'])[(laser_off)&(inds == i+1)],0))
    #                 binned_detector['off']['std'][i] = np.array(np.nanstd((processed_data[detector]/processed_data['I0_int_sum'])[(laser_off)&(inds == i+1)],0))

    #             if processed_data[detector].ndim == 2:

    #                 binned_detector['on']['sum'][i] = np.array(np.nansum((processed_data[detector]/processed_data['I0_int_sum'][:,np.newaxis])[(laser_on)&(inds == i+1)],0))
    #                 binned_detector['on']['mean'][i] = np.array(np.nanmean((processed_data[detector]/processed_data['I0_int_sum'][:,np.newaxis])[(laser_on)&(inds == i+1)],0))
    #                 binned_detector['on']['std'][i] = np.array(np.nanstd((processed_data[detector]/processed_data['I0_int_sum'][:,np.newaxis])[(laser_on)&(inds == i+1)],0))
    #                 binned_detector['off']['sum'][i] = np.array(np.nansum((processed_data[detector]/processed_data['I0_int_sum'][:,np.newaxis])[(laser_off)&(inds == i+1)],0))
    #                 binned_detector['off']['mean'][i] = np.array(np.nanmean((processed_data[detector]/processed_data['I0_int_sum'][:,np.newaxis])[(laser_off)&(inds == i+1)],0))
    #                 binned_detector['off']['std'][i] = np.array(np.nanstd((processed_data[detector]/processed_data['I0_int_sum'][:,np.newaxis])[(laser_off)&(inds == i+1)],0))
                    
    #         else:
    #             binned_detector['on']['sum'][i] = np.array(np.nansum(processed_data[detector][(laser_on)&(inds == i+1)],0))
    #             binned_detector['on']['mean'][i] = np.array(np.nanmean(processed_data[detector][(laser_on)&(inds == i+1)],0))
    #             binned_detector['on']['std'][i] = np.array(np.nanstd(processed_data[detector][(laser_on)&(inds == i+1)],0))
    #             binned_detector['off']['sum'][i] = np.array(np.nansum(processed_data[detector][(laser_off)&(inds == i+1)],0))
    #             binned_detector['off']['mean'][i] = np.array(np.nanmean(processed_data[detector][(laser_off)&(inds == i+1)],0))
    #             binned_detector['off']['std'][i] = np.array(np.nanstd(processed_data[detector][(laser_off)&(inds == i+1)],0))


    
    # return binned_detector
