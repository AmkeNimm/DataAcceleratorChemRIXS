import numpy as np
import h5py

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
        try:
            if hasattr(getattr(obj,key), "__len__"):
                summed = sumchan_helper(getattr(obj,key), rois[channel_dict[key]]) 
                setattr(obj, channel_dict[key], summed)
            #if we are parsing from the singleshot class this is an object
            #FIXME: implement option for getting channels from preproc or full area
            else:
                summed = sumchan_helper(getattr(getattr(obj,key),'preproc'),rois[channel_dict[key]]) 
                setattr(obj, channel_dict[key], summed)
        except:
            print(f'{key} does not exits ')

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


def bin_data(data,bin_axis,bins,scantype='fly'):
    #FIXME: do I call this function for each detector somewhere else, or do I loop through the detectors here
    # for now writing this for an individual detector, do on and off stuff outside this funciton too
    bin_axis = bin_axis.squeeze()
    print(bin_axis)
    if bin_axis.ndim > 1:
        raise ValueError('scanvar too many dimensions')
    idx = np.argsort(bin_axis)
    bin_axis = bin_axis[idx]
    data = data[idx]

    #Create bins depending on type of scan
    if scantype == 'fly':
        if bins[0] == 'Nbins':
            bin_counts, bin_edges = np.histogram(bin_axis, bins=bins[1], density=False)
        elif bins[0] == 'bin_width':
            Nbins = int((np.max(bin_axis)-np.min(bin_axis))/bins[1])
            bin_counts, bin_edges = np.histogram(bin_axis, bins=Nbins, density=False)
        #FIXME: option for bins with equal number of data points
        # elif  bins[0] == 'bin_count':
        #     Nbins = int(len(bin_axis)/bin_count)
        #     bin_edges = pd.cut(bin_axis,Nbins)

        else:
            raise ValueError('binning type unclear')
    
        print('bin_counts', len(bin_counts))
        print('bin_edges', len(bin_edges))
        
        bin_widths = bin_edges[1:] - bin_edges[:-1]
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
    elif scantype == 'step':
        scanvar = np.unique(bin_axis)
        bin_edges = scanvar

    elif scantype == 'static':
        bin_centers = np.mean(bin_axis)
        bin_edges = [np.mean(bin_axis)]
        bin_counts = len(bin_axis)
         
    else:
        raise ValueError('scan type for binning not defined')
    bin_edges = np.asarray(bin_edges)
    print(bin_edges)
    #FIXME: by using digitize are we excluding data points at both ends?

    ######
    #FIXME: does not seem to be working for delay scans
    # |
    # V
    #######
    print('bin_axis', np.min(bin_axis),bin_axis.max())
    print('bin_edges',np.min(bin_edges),bin_edges.max())
    print('bin_width', bin_widths[0])

    inds = np.digitize(bin_axis,bin_edges)
    print(inds)

    if data.ndim == 1:
        binned_dat_sum  = np.zeros(bin_edges.shape[0])
        binned_dat_mean = np.zeros(bin_edges.shape[0])
        binned_dat_std  = np.zeros(bin_edges.shape[0])
        
    elif data.ndim == 2:
        binned_dat_sum  = np.zeros([bin_edges.shape[0],data.shape[1]])
        binned_dat_mean = np.zeros([bin_edges.shape[0],data.shape[1]])
        binned_dat_std  = np.zeros([bin_edges.shape[0],data.shape[1]])
    else:
        raise ValueError('Detector shape not known')
    
    print('bin_counts',bin_counts)
    bin_counts =np.append(1,bin_counts[:])
    for i in np.arange(len(bin_edges)):
        if not sum((inds==i))==0:
            binned_dat_sum[i,:]  = np.nansum(data[inds==i],0)/bin_counts[i]
            binned_dat_mean[i,:] = np.nanmean(data[inds==i],0)
            binned_dat_std[i,:]  = np.nanstd(data[inds==i],0)


    return bin_centers, binned_dat_sum[1:,:], binned_dat_mean[1:,:], binned_dat_std[1:,:]

def myround(x, base=5):
    return base * np.round(x/base)

def get_premirror_pitch(premirror_pitch):
    try:
        return np.nanmean(myround(premirror_pitch,1))
    except:
        # This needs improving
        print('Add SP1K1:MONO:MMS:M_PI.RBV to epics config')
        return 144506
    
def mono_energy(pitchG,pitchM2,stateG = 'LRG', fname='../mono_calib.yml'):
    '''Calculator for RIXS mono calibration. This is the same function as what is saved to the mono eV epics variable. 
    pitchG: Grating pitch in urad
    pitchM2: Pre-mirror pitch in urad.
    '''
    import yaml
    with open(fname, 'r') as file:
        fy = yaml.safe_load(file)
    if stateG=='LRG':
        D0 = fy['D0_LRG']
        offsetG = fy['offsetG_LRG']
    elif stateG=='LEG':
        D0 = fy['D0_LEG']
        offsetG = fy['offsetG_LEG']
    elif stateG=='MEG':
        D0 = fy['D0_MEG']
        offsetG = fy['offsetG_LRG']
    elif stateG=='HEG':
        D0 = fy['D0_HEG']
        offsetG = fy['offsetG_HEG']

     # constants
    eVmm = 0.001239842 # Wavelenght[mm] = eVmm/Energy[eV]
    m = 1 # diffraction order

    pG = pitchG*1e-6 - offsetG
    pM2 = pitchM2*1e-6 - fy['offsetM2']
    alpha = np.pi/2 - pG + 2*pM2 - fy['thetaM1']
    beta = -np.pi/2 - pG + fy['thetaES']
    E = m*D0*eVmm/(np.sin(alpha) + np.sin(beta))
    Cff = np.cos(beta)/np.cos(alpha)

    #print('Calculated photon energy {0:6.2f} eV, Cff {1:3.2f}'.format(E, Cff))
    return E
 

def avg_data(runs, proc_folder):
    avg = {}
    with h5py.File(proc_folder+f'Run{runs[0]:04d}.h5','r') as tmp:
        keys = list(tmp.keys())
        for key in keys:
            avg[key] = np.zeros(tmp[key].shape)

    i=0
    for run in runs:
        i=i+1
        file = proc_folder+f'Run{run:04d}.h5'
        for key in keys:    
            with h5py.File(file,'r') as f:
                # print(f.keys())
                if avg[key].shape==f[key].shape:
                    avg[key] = avg[key] + f[key]
                else:
                    print(f'Run {run} shapes do not match')
    for key in keys:
        avg[key] = avg[key]/i
        return avg