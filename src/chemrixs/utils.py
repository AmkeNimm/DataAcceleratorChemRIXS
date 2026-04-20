import numpy as np
import h5py
import dask.array as da
import dask.dataframe as dd
import random

from scipy.optimize import curve_fit

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

    Returns
    -------
    fimsum : 1D array containing sum over ROI and channels

    '''
    # raw_fims=raw_fims.compute_chunk_sizes()
    if raw_fims.ndim == 3:    
        bg = (raw_fims[...,rois['bg_roi'][0]:rois['bg_roi'][1]]).mean(axis=-1)
        # print(raw_fims.shape)
        bgf = raw_fims - bg[...,None]
        fim_sum = np.zeros([bgf.shape[0],len(rois['channels'])])
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
        detector object containing fim or crixs data
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
        # try:
        a=getattr(obj,key)
        # print(a)
        if hasattr(getattr(obj,key), "__len__"):
            summed = sumchan_helper(getattr(obj,key), rois[channel_dict[key]]) 
            setattr(obj, channel_dict[key], summed)
        #if we are parsing from the singleshot class this is an object
        #FIXME: implement option for getting channels from preproc or full area
        else:
            summed = sumchan_helper(getattr(getattr(obj,key),'preproc'),rois[channel_dict[key]]) 
            setattr(obj, channel_dict[key], summed)
        # except:
        #     print(f'{key} does not exits ')

def normalise(dat, I0):
    '''
    Function to normalise a given signal to a given reference 
    
    Mostly normalisation of an n-dimensional detector signal by the X-ray intensities 

    Parameters
    ----------
    dat : array
        n-dimensional array with n e{1,2,3}, with one dimension being N = number of images
    I0 : dictionary
        1D array containing I0 for each corrected image

    Returns
    -------
    norm : normalised detector array
    '''
    #FIXME: not sure if I need to implement different cases for when dimensions are in a different order
    # dat.compute_chunk_sizes()
    # I0.compute_chunk_sizes()
    if dat.ndim == 1:
        norm = dat/I0
    elif dat.ndim == 2:
        norm = dat/I0[:,np.newaxis]
    elif dat.ndim == 3:
        norm = dat/I0[:,np.newaxis,np.newaxis]
    else:
        raise ValueError('Dimension do not match for normalising detector')
    return norm


def bin_data(data,bin_axis,bins,scantype='fly'):
    '''
    Function binning a given data set along a given binning variable
    
    Binning can be done for different scan types (fly or step scan), and independent of what the 
    scanvariable is. Different ways of binning can be determined

    Parameters
    ----------
    data : array
        n-dimensional array with n e{1,2,3}, with one dimension being N = number of images
    bin_axis : array
        1xN array containing the values of the scanvariable for each image 
    bins : list
        bins[0] determines the type of binning ('Nbins','bin_width','bin_edges')
        bin[1] defines for 
            'Nbins': number of bins
            'bin_width': the width of each bin
            'bin_edges': [start value, end value, #steps]

    Returns
    -------
    bin_centers: array
        binned scanvariable 
    binned_dat_sum : array
        n D array containing the data summed per bin
    binned_dat_mean : array
        n D array containing the data averaged per bin
    binned_dat_std : array
        n D array containing the standard deviation of the data per bin
    '''
    #FIXME: do I call this function for each detector somewhere else, or do I loop through the detectors here
    # for now writing this for an individual detector, do on and off stuff outside this funciton too
    bin_axis = bin_axis.squeeze()
    if bin_axis.ndim > 1:
        raise ValueError('scanvar too many dimensions')
    if False:
        idx = da.argsort(bin_axis)
    else:
        idx = np.argsort(bin_axis)

    #FIXME: for single shot we will need an approximate / chunked sort 

    
    bin_axis = bin_axis[idx]
    data = data[idx]

    #Create bins depending on type of scan
    if scantype == 'fly':
        print('fly)')
        if bins[0] == 'Nbins':
            print('Nbins')
            bin_counts, bin_edges = np.histogram(bin_axis, bins=bins[1], density=False)
        elif bins[0] == 'bin_width':
            print('bin_width')
            Nbins = int((np.max(bin_axis)-np.min(bin_axis))/bins[1])
            bin_counts, bin_edges = np.histogram(bin_axis, bins=Nbins, density=False)
        #FIXME: option for bins with equal number of data points
        elif  bins[0] == 'bin_edges':
            print('bin_edges')
            bin_edges = np.linspace(float(bins[1][0]),float(bins[1][1]),int(bins[1][2]))
            bin_counts, bin_edges1 = np.histogram(bin_axis, bin_edges, density=False)


        else:
            raise ValueError('binning type unclear')
    
        # print('bin_counts', len(bin_counts))
        # print('bin_edges', len(bin_edges))
        
        bin_widths = bin_edges[1:] - bin_edges[:-1]
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
    elif scantype == 'step':
        scanvar,bin_counts = np.unique(bin_axis,return_counts=True)
        print(f'scanvar in bin_data {len(scanvar)}')
        bin_edges = scanvar
        bin_widths = bin_edges[1:] - bin_edges[:-1]
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    elif scantype == 'static':
        bin_centers = np.mean(bin_axis)
        bin_edges = [np.mean(bin_axis)]
        bin_counts = len(bin_axis)
        bin_widths = bin_edges[1:] - bin_edges[:-1]
         
    else:
        raise ValueError('scan type for binning not defined')
    bin_edges = np.asarray(bin_edges)
    # print(bin_edges)
    #FIXME: by using digitize are we excluding data points at both ends?

    ######
    #FIXME: does not seem to be working for delay scans
    # |
    # V
    #######
    # print('bin_axis', np.min(bin_axis),bin_axis.max())
    # print('bin_edges',np.min(bin_edges),bin_edges.max())
    # print('bin_width', bin_widths)

    inds = np.digitize(bin_axis,bin_edges)
    # print(inds)

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
    #FIXME: normalisation by bin counts missing
    # print('bin_counts',bin_counts)
    # bin_counts =np.append(1,bin_counts[:])
    for i in np.arange(len(bin_edges)):
        if not sum((inds==i))==0:
            binned_dat_sum[i,:]  = np.nansum(data[inds==i],0)#/bin_counts[i]
            binned_dat_mean[i,:] = np.nanmean(data[inds==i],0)
            binned_dat_std[i,:]  = np.nanstd(data[inds==i],0)


    return bin_centers, binned_dat_sum[1:,:], binned_dat_mean[1:,:], binned_dat_std[1:,:], bin_counts

def myround(x, base=5):
    return base * np.round(x/base)

def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx

def get_premirror_pitch(premirror_pitch):
    try:
        return np.nanmean(myround(premirror_pitch,1))
    except:
        # This needs improving
        print('Add SP1K1:MONO:MMS:M_PI.RBV to epics config')
        return 144506
    
def mono_energy(pitchG,pitchM2,stateG = 'LRG', fname='../mono_calib.yml'):
    '''Calculator for RIXS mono calibration. This is the same function as 
    what is saved to the mono eV epics variable. 
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
 

def avg_data(runs : list, proc_folder : str = '',proc_path : str = ''):
    avg = {}
    with h5py.File(proc_folder+f'{runs[0]:04d}.h5','r') as tmp:
        keys = list(tmp.keys())
        # print(keys)
        for key in keys:
            avg[key] = np.zeros(tmp[key].shape)

    i=0
    for run in runs:
        i=i+1
        file = proc_folder+f'{run:04d}.h5'
        # FIXME: 
        for key in keys:    
            with h5py.File(file,'r') as f:
                if avg[key].shape==f[key].shape:
                    avg[key] = avg[key] + np.asarray(f[key])
                    # print(f[key])
                else:
                    #FIXME: Here implement stuff for stitching
                    print(f'Run {run} {key} shapes do not match')
            
    for key in keys:
        avg[key] = avg[key]/i
    return avg

# ### **Uncertainty Formula for unweighted Average**:
# [\sigma_{\bar{x}} = \frac{1}{\sqrt{N}} \sqrt{\sum_{i=1}^{N} \sigma_i^2}]
   

def avg_data_count(runs : list, proc_folder : str = '',proc_path : str = ''):
    avg = {}
    with h5py.File(proc_folder+f'{runs[0]:04d}.h5','r') as tmp:
        keys = list(tmp.keys())
        if 'counts_on' in keys:
            counts_on = np.zeros(tmp['counts_on'].shape)
            counts_off = np.zeros(tmp['counts_off'].shape)
            laser = True
        else:
            counts = np.zeros(tmp['counts'].shape)
            laser = False

        # print(keys)
        for key in keys:
            avg[key] = np.zeros(tmp[key].shape)

    i=0
    for run in runs:
        i=i+1
        file = proc_folder+f'{run:04d}.h5'

        #load processed data
        with h5py.File(file,'r') as f:
            # define count
            if laser:
                count_on = np.asarray(f['counts_on'])
                count_off = np.asarray(f['counts_off'])
                laser = True
            else:
                count = np.asarray(f['counts'])

            # do count-weighted averaging
            for key in keys:
                if laser:
                    if 'on' in key:
                        count = count_on
                    elif 'off' in key:
                        count = count_off
                else:
                    count = count

                if avg[key].shape==f[key].shape:
                    if len(avg[key].shape) == 1:
                        avg[key] = avg[key] + np.asarray(f[key])*count
                    else:
                        avg[key] = avg[key] + np.asarray(f[key])*count[:,np.newaxis]
                else:
                    #FIXME: Here implement stuff for stitching
                    print(f'Run {run} {key} shapes do not match')
        # Sum counts per scanvar
        if laser:
            counts_on = counts_on + count_on
            counts_off = counts_off + count_off
            print(counts_off)

        else:
            counts = counts + count
    # Divide by count per scanvar
    for key in keys:
        if laser:
            if 'on' in key:
                if len(avg[key].shape) == 1:
                    avg[key] = avg[key]/counts_on
                else:
                    avg[key] = avg[key]/counts_on[:,np.newaxis]
            elif 'off' in key:
                if len(avg[key].shape) == 1:
                    avg[key] = avg[key]/counts_off
                else:
                    avg[key] = avg[key]/counts_off[:,np.newaxis]
        else:
            if len(avg[key].shape) == 1:
                avg[key] = avg[key]/counts
            else:
                avg[key] = avg[key]/counts[:,np.newaxis]
    return avg

#FIXME

# ### **Uncertainty Formula for Weighted Average**:

# [
# \sigma_{\bar{x}*{\text{w}}} = \sqrt{\frac{1}{\sum*{i=1}^{N} w_i^2} \sum_{i=1}^{N} w_i^2 \sigma_i^2}
# ]

# Where:

# * ( \sigma_{\bar{x}_{\text{w}}} ) is the uncertainty in the weighted average.
# * ( w_i ) are the weights.
# * ( \sigma_i ) are the individual uncertainties for each measurement.


def pixel2emi(pixel, dat, mono=[], calib=[], points=[], w_calib_line=10, plot=True):
    if calib == []:
        if mono == []:
            raise TypeError('Need mono energies for emission calibration')
        else:
            emi,calib = calib_emi(mono, dat, points, w_calib_line=w_calib_line, plot=plot)
    else:
        emi = pixel*calib[0]+calib[1]

    return(emi,calib)

def emi2ET(mono,emission,data,std,step):
   
    
    Etrans_in = np.zeros(data.shape)
    
    for i in np.arange(len(mono)):
        for j in np.arange(len(emission)):
            Etrans_in[i,j] = mono[i]-emission[j]
            
            
    Emin = np.max(np.min(Etrans_in))
    Emax = np.min(np.max(Etrans_in))
    
    E_trans = np.arange(Emin,Emax+step,step)
    
    data_trans = np.zeros([len(mono), len(E_trans)])
    std_trans = np.zeros([len(mono), len(E_trans)])
    
    for i in np.arange(len(E_trans)-1):
        for ii in np.arange(len(mono)):
            mask = np.logical_and(Etrans_in[ii,:] > E_trans[i],
                      Etrans_in[ii,:] < E_trans[i+1])
            N = len(data[ii, mask])
            data_trans[ii,i] = np.nanmean(data[ii, mask])
            std_trans[ii,i] = np.sqrt(np.sum(std[ii, mask]**2)) / N
            
    data_trans[np.isnan(data_trans)] = 0
    std_trans[np.isnan(std_trans)] = 0
            
    return mono, E_trans, data_trans,std_trans

def calib_emi(mono, dat, end_points_el, w_calib_line=5, plot=True):
    #FIXME
    ix1 = find_nearest(mono,end_points_el[0][0])
    ix2 = find_nearest(mono,end_points_el[1][0])
    iy1 = end_points_el[0][1]
    iy2 = end_points_el[1][1]

    nx, ny = dat.shape

        # --- Fit center line y ≈ m*x + c in (mono units -> pixel)
    # Use the axis values (mono[ix]) for x
    x_vals = np.array([mono[ix1], mono[ix2]], dtype=float)
    y_vals = np.array([iy1, iy2], dtype=float)
    #y = m*x+c
    m = (iy2-iy1)/(mono[ix2]-mono[ix1])
    c = iy1-m*mono[ix1]

    mono_points = []
    ypix_at_max = []

    # --- Scan each x index within the span; search along y within top/bottom bounds
    for ix in np.arange(ix1, ix2 + 1):
        x_here = mono[ix]
        y_center = m * x_here + c
        y_lo = int(np.floor(y_center - w_calib_line/2))
        y_hi = int(np.ceil (y_center + w_calib_line/2))
        
        if y_hi < y_lo:
            y_lo, y_hi = [y_hi, y_lo]

        rixs_slice = dat[ix, y_lo:y_hi + 1]
        if rixs_slice.size == 0 or np.all(np.isnan(rixs_slice)):
            continue

        rel = int(np.nanargmax(rixs_slice))
        iy_max = y_lo + rel

        mono_points.append(x_here)
        ypix_at_max.append(iy_max)

    mono_points = np.asarray(mono_points)
    ypix_at_max = np.asarray(ypix_at_max)

    a,b = np.polyfit(ypix_at_max, mono_points, 1)
    emi = np.polyval([a, b], np.arange(ny))

    if plot_on:
        plt.figure(figsize=(7, 6))
        # Display Z with axes: x = mono (horizontal), y = pixel (vertical)
        extent = [mono.min(), mono.max(), 0, ny - 1]
        # plt.imshow(Z.T, origin='lower', extent=extent, aspect='auto')
        plt.pcolormesh(mono,range(0,dat.shape[1]),dat.T,cmap='terrain_r')
        plt.colorbar(label='Intensity')

        # Draw the two points
        plt.scatter([x_vals[0], x_vals[1]], [y_vals[0], y_vals[1]],
                    s=60, c='white', edgecolor='k', label='given points')
        plt.scatter(mono_points, ypix_at_max,
                    s=60, c='white', edgecolor='k', label='given points')

        # Draw center and top/bottom edges
        x_line = np.linspace(mono[ix1], mono[ix2], 200)
        y_center = m * x_line + c
        y_top = y_center +  w_calib_line/2
        y_bot = y_center -  w_calib_line/2
        plt.plot(x_line, y_center, 'w--', lw=1.5, label='center line',color='k')
        plt.plot(x_line, y_top,    'w-',  lw=1.0, alpha=0.8,color='k')
        plt.plot(x_line, y_bot,    'w-',  lw=1.0, alpha=0.8,color='k')

        # Scatter maxima used for the fit
        plt.scatter(mono_points, ypix_at_max, s=20, c='yellow', edgecolor='k', label='max @ each x')

        # Plot fitted calibration line (x vs pixel)
        ypix = np.arange(ny)
        plt.plot(np.polyval([a, b], ypix), ypix, 'r-', lw=2,
                 label=f'fit: mono = {a:.6g} * pixel + {b:.6g}')
        plt.xlim(mono[0],mono[-1])
        plt.xlabel('Energy (mono)')
        

    return emi, [a,b]


def gaussian_moments(x, y):
    """
    Fast Gaussian fit using moments.

    Returns
    -------
    A     : amplitude
    mu    : center
    sigma : width
    C     : offset
    """

    # estimate offset from edges
    C = np.median(np.concatenate([y[:10], y[-10:]]))
    y0 = y - C

    # guard against bad curves
    if np.all(y0 <= 0):
        return np.nan, np.nan, np.nan, C

    y0 = np.clip(y0, 0, None)

    norm = np.sum(y0)
    mu = np.sum(x * y0) / norm
    sigma = np.sqrt(np.sum((x - mu)**2 * y0) / norm)
    A = np.max(y0)

    return A, mu, sigma, C


def gaussian(x, A, mu, sigma, C):
    return A * np.exp(-(x - mu)**2 / (2 * sigma**2)) + C

def gaussian_linear(x, A, mu, sigma, C, D):
    return A * np.exp(-(x - mu)**2 / (2 * sigma**2)) + (C + D * x)

def asymmetric_gaussian(x, A, mu, sigma1, sigma2,C,D):
    return np.where(x < x0,
                    A * np.exp(-((x - mu)**2) / (2 * sigma1**2)),
                    A * np.exp(-((x - mu)**2) / (2 * sigma2**2)))+D*x+C

def gaussian_moments_linear(x, y):
    """
    Fast Gaussian fit using moments with linear baseline.

    Returns
    -------
    A     : amplitude
    mu    : center
    sigma : width
    C     : baseline intercept
    D     : baseline slope
    """

    # estimate baseline from edges
    n = min(10, len(x) // 2)
    x_edges = np.concatenate([x[:n], x[-n:]])
    y_edges = np.concatenate([y[:n], y[-n:]])

    # linear fit to edges
    D, C = np.polyfit(x_edges, y_edges, 1)

    baseline = C + D * x
    y0 = y - baseline

    # guard against bad curves
    if np.all(y0 <= 0):
        return np.nan, np.nan, np.nan, C, D

    y0 = np.clip(y0, 0, None)

    norm = np.sum(y0)
    mu = np.sum(x * y0) / norm
    sigma = np.sqrt(np.sum((x - mu)**2 * y0) / norm)
    A = np.max(y0)

    return A, mu, sigma, C, D



def fit_gaussian_fast(x, y, lb, ub):
    p0 = gaussian_moments(x, y)
    bounds = [lb, ub]

    if np.any(np.isnan(p0[:3])):
        return p0

    try:
        p0=np.asarray(p0)
        p0[p0<lb]= lb[p0<lb]
        p0[p0>ub]= ub[p0>ub]
        popt, _ = curve_fit(
            gaussian,
            x,
            y,
            p0=p0,
            bounds=bounds,
            maxfev=2000
        )
        return popt
    except RuntimeError:
        return p0
    

def fit_gaussian_fast_linear(x, y, lb, ub):
    tmp = gaussian_moments_linear(x, y)
    p0 = [tmp[0],tmp[1],tmp[2],tmp[2],tmp[3],tmp[4]]
    bounds = [lb, ub]

    if np.any(np.isnan(p0[:3])):
        return p0

    try:
        p0 = np.asarray(p0)
        p0[p0 < lb] = lb[p0 < lb]
        p0[p0 > ub] = ub[p0 > ub]

        popt, _ = curve_fit(
            # gaussian_linear,
            asymmetric_gaussian, #(x, A, mu, sigma1, sigma2,C,D)
            x,
            y,
            p0=p0,
            bounds=bounds,
            maxfev=3000
        )
        return popt
    except RuntimeError:
        return p0


def reconst_svd(u,s,v,N):
    
    data_denoised = (u[:, :N] * s[:N]) @ v[:N, :]
    return data_denoised

def reconst_singlecomp(u,s,v,x):
    component_x = s[x] * np.outer(u[:, x], v[x, :])
    return component_x


# LS Waveform SVD functions 
def decomp_(waves,nevts):    
    # randomly pick up nevts events
    if nevts<waves.shape[0]:
        idx = np.array(random.sample(range(0,waves.shape[0]),nevts))
        # print(idx)
    else:
        idx = np.arange(waves.shape[0])
    start,end = (0,waves.shape[1])  #which section of waveform to use for svd.  use to select out saturation region

    #instead manually calculate svd by using the smaller lh sv.
    s,u = np.linalg.eigh(np.dot(waves[idx,start:end],waves[idx,start:end].transpose()))
    v = np.dot(np.linalg.pinv(u),waves[idx,start:end])

 # get the real component of the eigenvector
    temp = np.array([i/np.dot(i,i)**0.5 for i in v[:]])#normalizing
    v = np.real(temp)
    #print(s.shape,v.shape, np.flipud(s).shape, np.flipud(v).shape)
    return np.flipud(v)[:1000],np.flipud(s)[:1000]


def decomp_1d(vec_dark,val_dark,wfs,ROI_svd,neigs = 2):  # this function does pixel-resolved singular value decomposition
    # ROI SVD 
    #print(val_dark[:neigs].sum()/val_dark.sum())
    target_1d = wfs
    bg_mask = (wfs[0]*0+1).astype(bool)
    bg_mask[ROI_svd[0]:ROI_svd[1]]=False 
    signal_1d = target_1d/np.dot(np.dot(target_1d[:,bg_mask],np.linalg.pinv(vec_dark[:neigs][:,bg_mask])),vec_dark[:neigs])

    return signal_1d[:,ROI_svd[0]:ROI_svd[1]]

# v, s = decomp_(dat[loff],2000) #decomposition of BG data (dark)
# sl = slice(0,-1)
# traces = decomp_1d(v,s,dat[:,:][:],ROI) #all data only ROI



def standard_error_IO(data_matrix):
    '''
    Function to determine the standard error for a distribution with on and off shots and varying intensity of on.

    An example is the SVLS detector after dropletting where each pixel has a value of either 0 or several 100s ADUs

    Parameters
    ----------
    data_matrix : float
    2D matrix containing the raw data with data_matrix.shape[0] is the number of shots

    Returns
    -------
    uncertainty_sum : float
    Array containing the standard error for the sum of all values in bin

    datsum : float
    Array containing the sum of all values in bin

    standard_error_mean : float
    Array containing the standard error for the mean of all values in bin

    datmean : float
    Array containing the mean of all values in bin

    '''
    # Number of shots (N)
    N = data_matrix.shape[0]

    # Determine p_on (proportion of non-zero values for each pixel)
    p_on = np.nansum(data_matrix > 0, axis=0) / N

    # Determine V_on_mean (mean of non-zero values for each pixel)
    V_on_mean = np.divide(
                    np.nansum(data_matrix, axis=0),
                    np.nansum(data_matrix > 0, axis=0),
                    out=np.zeros_like(np.nansum(data_matrix, axis=0), dtype=float),
                    where=np.nansum(data_matrix > 0, axis=0) != 0
                    )

    # Determine V_on_std (standard deviation of non-zero values for each pixel)
    V_on_std = np.nanstd(data_matrix * (data_matrix > 0), axis=0)

    # Calculate the variance for each pixel (row)
    variance_signal = p_on * (V_on_std**2 + V_on_mean**2)

    # # Standard error of the mean for each pixel
    standard_error_mean = np.sqrt(variance_signal) / np.sqrt(N) #if N shots is 0 we got a different problem

    # Uncertainty in the total sum for each pixel
    uncertainty_sum = np.sqrt(N) * np.sqrt(variance_signal)

    datsum = np.nansum(data_matrix,axis=0)

    datmean = np.nanmean(data_matrix,axis=0)

    return datsum, uncertainty_sum, datmean, standard_error_mean



def bin_svls(data,bin_axis,bins,scantype='fly'):
    '''
    Function binning a given data set along a given binning variable
    
    Binning can be done for different scan types (fly or step scan), and independent of what the 
    scanvariable is. Different ways of binning can be determined

    Parameters
    ----------
    data : array
        n-dimensional array with n e{1,2,3}, with one dimension being N = number of images
    bin_axis : array
        1xN array containing the values of the scanvariable for each image 
    bins : list
        bins[0] determines the type of binning ('Nbins','bin_width','bin_edges')
        bin[1] defines for 
            'Nbins': number of bins
            'bin_width': the width of each bin
            'bin_edges': [start value, end value, #steps]

    Returns
    -------
    bin_centers: array
        binned scanvariable 
    binned_dat_sum : array
        n D array containing the data summed per bin
    binned_dat_mean : array
        n D array containing the data averaged per bin
    binned_dat_std : array
        n D array containing the standard deviation of the data per bin
    '''
    #FIXME: do I call this function for each detector somewhere else, or do I loop through the detectors here
    # for now writing this for an individual detector, do on and off stuff outside this funciton too
    bin_axis = bin_axis.squeeze()
    if bin_axis.ndim > 1:
        raise ValueError('scanvar too many dimensions')
    if False:
        idx = da.argsort(bin_axis)
    else:
        idx = np.argsort(bin_axis)

    #FIXME: for single shot we will need an approximate / chunked sort 

    
    bin_axis = bin_axis[idx]
    data = data[idx]

    #Create bins depending on type of scan
    if scantype == 'fly':
        print('fly)')
        if bins[0] == 'Nbins':
            print('Nbins')
            bin_counts, bin_edges = np.histogram(bin_axis, bins=bins[1], density=False)
        elif bins[0] == 'bin_width':
            print('bin_width')
            Nbins = int((np.max(bin_axis)-np.min(bin_axis))/bins[1])
            bin_counts, bin_edges = np.histogram(bin_axis, bins=Nbins, density=False)
        #FIXME: option for bins with equal number of data points
        elif  bins[0] == 'bin_edges':
            print('bin_edges')
            bin_edges = np.linspace(float(bins[1][0]),float(bins[1][1]),int(bins[1][2]))
            bin_counts, bin_edges1 = np.histogram(bin_axis, bin_edges, density=False)


        else:
            raise ValueError('binning type unclear')
    
        # print('bin_counts', len(bin_counts))
        # print('bin_edges', len(bin_edges))
        
        bin_widths = bin_edges[1:] - bin_edges[:-1]
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
    elif scantype == 'step':
        scanvar,bin_counts = np.unique(bin_axis,return_counts=True)
        print(f'scanvar in bin_data {len(scanvar)}')
        bin_edges = scanvar
        bin_widths = bin_edges[1:] - bin_edges[:-1]
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    elif scantype == 'static':
        bin_centers = np.mean(bin_axis)
        bin_edges = [np.mean(bin_axis)]
        bin_counts = len(bin_axis)
        bin_widths = bin_edges[1:] - bin_edges[:-1]
         
    else:
        raise ValueError('scan type for binning not defined')
    bin_edges = np.asarray(bin_edges)
    # print(bin_edges)
    #FIXME: by using digitize are we excluding data points at both ends?

    ######
    #FIXME: does not seem to be working for delay scans
    # |
    # V
    #######
    # print('bin_axis', np.min(bin_axis),bin_axis.max())
    # print('bin_edges',np.min(bin_edges),bin_edges.max())
    # print('bin_width', bin_widths)

    inds = np.digitize(bin_axis,bin_edges)
    # print(inds)

    if data.ndim == 1:
        binned_dat_sum  = np.zeros(bin_edges.shape[0])
        binned_dat_sumerr  = np.zeros(bin_edges.shape[0])
        binned_dat_mean = np.zeros(bin_edges.shape[0])
        binned_dat_std  = np.zeros(bin_edges.shape[0])
        
    elif data.ndim == 2:
        binned_dat_sum  = np.zeros([bin_edges.shape[0],data.shape[1]])
        binned_dat_sumerr  = np.zeros([bin_edges.shape[0],data.shape[1]])
        binned_dat_mean = np.zeros([bin_edges.shape[0],data.shape[1]])
        binned_dat_std  = np.zeros([bin_edges.shape[0],data.shape[1]])
    else:
        raise ValueError('Detector shape not known')
    #FIXME: normalisation by bin counts missing
    # print('bin_counts',bin_counts)
    # bin_counts =np.append(1,bin_counts[:])
    for i in np.arange(len(bin_edges)):
        if not sum((inds==i))==0:
            binned_dat_sum[i,:], binned_dat_sumerr[i,:], binned_dat_mean[i,:], binned_dat_std[i,:]  = standard_error_IO(data[inds==i])  #/bin_counts[i]
        

    return bin_centers, binned_dat_sum[1:,:], binned_dat_sumerr[1:,:], binned_dat_mean[1:,:], binned_dat_std[1:,:], bin_counts


def get_PFY(rixs,std):
    PFY     = np.sum(rixs, axis=1)
    PFY_std = np.sqrt(np.nansum(std**2, axis=1))
    return PFY, PFY_std


def get_CIE(Ecie,width,Einc,data_trans,std_trans):
    '''
    Obtain constant incident energy cut from data matrix with incident energy and energy transfer as axes
    
    Parameters
    ----------
    
    Ecie : float
    energy at which to take CIE cut

    width : integer
    how many pixels left and right of Ecie to include in CIE

    Einc : array
    incident energy axis

    data_trans : array (mxn)
    rixs data in a incident energy vs energy transfer matrix

    std_trans : array (mxn)
    standard deviation of rixs data in a incident energy vs energy transfer matrix


    '''

    inds = np.argmin(np.abs(Einc-Ecie))
    CIE     = np.nansum(data_trans[inds-width:inds+width,:],axis=0)
    CIE_std = np.sqrt(np.nansum(std_trans[inds-width:inds+width,:]**2, axis=0))
    return CIE, CIE_std