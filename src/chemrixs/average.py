
import h5py
import matplotlib.pyplot as plt
import numpy as np
import os
import yaml

from functools import cached_property
from pathlib import Path
from chemrixs.utils import *
from chemrixs.process import Reduced

class Average():
    """
    A class to average over several runs. 

    Takes runnumber as input, if these runs have been processed before
    they will simply be averaged, otherwise the 'Reduced' class is called 
    to process these runs first.

    Parameters
    ----------
    runs : list
        containing the integers of the runs to average

    proc_path : str or Path
        The filename structure and location of the processed runs. 
        Should be complete by simply adding the '{run:04d}.h5'

    avg : str
        String determining the way of averaging: 

    output_path : str or Path
        The filename for the output of averaged data.
    
    
    raw_path : str or Path
        The filename structure for the data to analyse.
        Should be complete by simply adding the '{run:04d}.h5'

    bgpath : str or Path
        The filename for a darkscan that can be used for background subtraction.

    fyaml : str or Path
        yaml file with settings for processing of unprocessed runs.

    bgyaml : str or Path
        yaml file with settings for processing the BG data, needed for unprocessed runs.

    save : bool
        Boolean determining if the processed data should be saved where processing necessary.

    scantype : str
        Optional, determining the type of scan for processing. If not given, this will be
        determined by the data structure.

    norm : bool
        Boolean determining if data should be normalised by I0 or not when processing.
        
    """

    def __init__(self, runs: list | int, proc_path: str | Path, avg: str, output_path: str | Path,
                raw_path: str | Path, bgpath: str | Path, fyaml: str | Path, bgyaml: str | Path, 
                save: bool = True, scantype: str = '',norm: bool = True):
        
        self.runs = runs
        self.proc_path = proc_path
        self.avg = avg
        self.output_path = output_path

        try:
            with open(fyaml, 'r') as file:
                 self.yaml = yaml.safe_load(file)
        except FileNotFoundError as fe: 
            raise FileNotFoundError('Config yaml file not found - check filename') from fe


        if len(raw_path) is not None:
            self.raw_path = raw_path
            self.bgpath = bgpath
            self.fyaml = fyaml
            self.bgyaml = bgyaml
            self.scantype = scantype
            self.norm = norm

        self.check_reduce()
        self.average


    def check_reduce(self):
        for run in self.runs:
            proc_path = self.proc_path + f'{run:04d}.h5'
            if os.path.isfile(proc_path) == False:
                fname = self.raw_path + f'{run:04d}.h5'
                tmp = Reduced(fname,self.bgpath,self.fyaml,self.bgyaml, 
                        save=True,scantype=self.scantype,norm=self.norm)
                self.scantype = tmp.data.scantype

        
        return
    
    @cached_property
    def average(self):
        print(self.proc_path)
        try:
            avg = avg_data_count(self.runs, self.proc_path)
        except:
            print('not count averaged')
            avg = avg_data(self.runs, self.proc_path)

        return avg
    
    def get_emi(self):
        px = np.arange(self.average['axis_svls_off_mean'].shape[1])

        for i in np.arange(len(self.yaml['emi_calib'])):
            emi_config = np.asarray(self.yaml['emi_calib'][i])
            if np.logical_and(np.all(self.runs>emi_config[0]),np.all(self.runs<emi_config[1])):
                emi_calib = emi_config[2:4]
                print(emi_calib)
        emi = emi_calib[0]*px+emi_calib[1]
        return emi

    def plot_svls2D(self, calibrated=True,savefig=False,transparent=True,figsize=(12,8),scale=1):
        if calibrated == True:
            emi = self.get_emi()
            self.average['E_emi'] = emi
        else:
            print('emission is not calibrated')
            emi = np.arange(self.average['axis_svls_off_mean'].shape[1])

        ddatmax = np.nanmax(self.average['axis_svls_on_mean'].T-self.average['axis_svls_off_mean'].T)
 
        fig,ax = plt.subplots(1,3,sharex=True, sharey=True,figsize=figsize)
        ax[0].pcolor(self.average['scanvar_on'],emi,(self.average['axis_svls_off_mean']).T,cmap = 'Reds',
                     vmin=0,vmax=np.nanmax(self.average['axis_svls_off_mean'])/scale)
        ax[1].pcolor(self.average['scanvar_on'],emi,(self.average['axis_svls_on_mean']).T,cmap = 'Reds',
                     vmin=0,vmax=np.nanmax(self.average['axis_svls_on_mean'])/scale)
        ax[2].pcolor(self.average['scanvar_on'],emi,(self.average['axis_svls_on_mean']).T-(self.average['axis_svls_off_mean']).T,cmap = 'bwr',
                     vmin=-ddatmax,vmax=ddatmax)

        ax[0].set_xlabel('inc. energy (eV)')
        ax[1].set_xlabel('inc. energy (eV)')
        ax[2].set_xlabel('inc. energy (eV)')

        if calibrated == True:
            ax[0].set_ylabel('emission (pixel)')
        else:
            ax[0].set_ylabel('emission (pixel)')

        ax[0].set_title('laser off')
        ax[1].set_title('laser on')
        ax[2].set_title('difference')

        ax[0].set_xlim([np.nanmin(self.average['scanvar_on']),np.nanmax(self.average['scanvar_on'])])
        ax[0].set_title(f'Runs {self.runs[0]} to {self.runs[-1]}')

        if savefig:
            fig.savefig(f'figs/SVLS2D_{self.runs[0]}_{self.runs[-1]}.png',transparent=transparent,
                        dpi=200, bbox_inches='tight')

        # return fig

    def plot_svls1D(self,savefig=False,transparent=True,figsize=(12,8)):
        """
        Plotting binned and averaged SVLS detector, collapsed on scanvar axis.
        
        :param self: Description
        """
        
        fig,ax = plt.subplots(1,3,sharex=True, sharey=True,figsize=figsize)
        ax[0].plot(self.average['scanvar_off'],np.nanmean(self.average['axis_svls_off_mean'],axis=1))
        ax[1].plot(self.average['scanvar_on'],np.nanmean(self.average['axis_svls_on_mean'],axis=1))
        ax[2].plot(self.average['scanvar_on'],np.nanmean(self.average['axis_svls_on_mean']-self.average['axis_svls_off_mean'],axis=1))
        if self.scantype=='mono_fly':
            ax[0].set_xlabel('inc. energy (eV)')
            ax[1].set_xlabel('inc. energy (eV)')
            ax[2].set_xlabel('inc. energy (eV)')
        elif self.scantype=='delay_fly':
            ax[0].set_xlabel('delay (s)')
            ax[1].set_xlabel('delay (s)')
            ax[2].set_xlabel('delay (s)')
        ax[0].set_xlim([np.nanmin(self.average['scanvar_on']),np.nanmax(self.average['scanvar_on'])])
        ax[0].set_title(f'Runs {self.runs[0]} to {self.runs[-1]}')
    
    def plot_svls2D_ET(self, savefig=False,transparent=True,figsize=(12,8),scale=1):
        try:
            emi = self.get_emi()
        except:
            print('emission is not calibrated, cannot plot energy transfer')
        
        mono_on, E_trans_on, data_trans_on = emi2ET(self.average['scanvar_on'],emi,self.average['axis_svls_on_mean'],.2)
        mono_off, E_trans_off, data_trans_off = emi2ET(self.average['scanvar_off'],emi,self.average['axis_svls_off_mean'],.2)

        self.average['mono_on'] = mono_on
        self.average['mono_off'] = mono_off
        self.average['E_trans_on'] = E_trans_on
        self.average['E_trans_off'] = E_trans_off
        self.average['data_trans_on'] = data_trans_on
        self.average['data_trans_off'] = data_trans_off
            

        ddatmax = np.nanmax(self.average['axis_svls_on_mean'].T-self.average['axis_svls_off_mean'].T)
 
        fig,ax = plt.subplots(1,3,sharex=True, sharey=True,figsize=figsize)
        ax[0].pcolor(mono_on,E_trans_on,data_trans_on.T,cmap = 'Reds',
                     vmin=0,vmax=np.nanmax(data_trans_on)/scale,shading='auto')
        ax[1].pcolor(mono_off,E_trans_off,data_trans_off.T,cmap = 'Reds',
                     vmin=0,vmax=np.nanmax(data_trans_off)/scale,shading='auto')
        ax[2].pcolor(mono_on,E_trans_on,(data_trans_on-data_trans_off).T,cmap = 'bwr',
                     vmin=-ddatmax,vmax=ddatmax,shading='auto')

        ax[0].set_xlabel('inc. energy (eV)')
        ax[1].set_xlabel('inc. energy (eV)')
        ax[2].set_xlabel('inc. energy (eV)')

        ax[0].set_ylabel('emission (pixel)')

        ax[0].set_title('laser off')
        ax[1].set_title('laser on')
        ax[2].set_title('difference')

        ax[0].set_xlim([np.nanmin(self.average['scanvar_on']),np.nanmax(self.average['scanvar_on'])])
        ax[0].set_title(f'Runs {self.runs[0]} to {self.runs[-1]}')

        if savefig:
            fig.savefig(f'figs/SVLS2D_{self.runs[0]}_{self.runs[-1]}.png',transparent=transparent,
                        dpi=200, bbox_inches='tight')
            

    def elastic_calibrate_from_two_points(self,
        mono,
        rixs_map_full,
        p1, p2,
        width_pixels=20,
        plot_on=True
        ):
        """
        Calibrate using a parallelogram ROI defined by two points and a fixed width.

        Parameters
        ----------
        mono : (nx,) array
            X-axis values (energy). Assumed monotonic; used on FIRST axis of rixs_map_full.
        rixs_map_full : (nx, ny) array
            2D map with first index along mono (x), second index = pixel (y).
        p1, p2 : tuple
            Two points defining the *center line* of the ROI, as (x_value_in_mono_units, y_pixel_index).
            Example: p1 = (x1, y1_pixel), p2 = (x2, y2_pixel).
        width_pixels : int or float
            Total vertical thickness of the parallelogram in pixels (constant in y).
            Top/Bottom are ±width/2 around the center line y(x) in pixel space.
        plot_on : bool
            If True, show a diagnostic plot.

        Returns
        -------
        calibrated_axis : (ny,) array
            mono ≈ a*pixel + b evaluated over all pixels.
        fit : (a, b)
            Linear fit parameters such that mono ≈ a*pixel + b.
        details : dict
            Extra info: sampled (x_mono, y_pix) of maxima, indices, etc.
        """
        mono = np.asarray(mono)
        Z = np.asarray(rixs_map_full)
        nx, ny = Z.shape

        # --- Convert the two points to (ix, iy) using mono -> x index
        x1, y1 = p1
        x2, y2 = p2
        ind_x1 = find_nearest(mono, x1)
        ind_x2 = find_nearest(mono, x2)
        px_y1 = int(round(y1))
        px_y2 = int(round(y2))
        # --- Center line
        m =(px_y2-px_y1)/(mono[ind_x2]-mono[ind_x1])
        c = px_y1-m*mono[ind_x1]

        half_w = 0.5 * float(width_pixels)

        # --- Determine x-span (in indices) to scan
        ix_start = min(ind_x1, ind_x2)
        ix_end   = max(ind_x1, ind_x2)

        x_samples = []
        ypix_at_max = []
        used_ix = []

        # --- Scan each x index within the span; search along y within top/bottom bounds
        for i in range(ix_start, ix_end + 1):
            x_here = mono[i]
            y_center = m * x_here + c
            y_lo = int(np.floor(y_center - half_w))
            y_hi = int(np.ceil (y_center + half_w))
            if y_lo > y_hi:
                y_lo, y_hi = y_hi, y_lo
            y_lo = max(0, min(ny - 1, y_lo))
            y_hi = max(0, min(ny - 1, y_hi))
            if y_hi < y_lo:
                continue

            col_slice = Z[i, y_lo:y_hi + 1]
            if col_slice.size == 0 or np.all(np.isnan(col_slice)):
                continue

            rel = int(np.nanargmax(col_slice))
            iy_max = y_lo + rel

            x_samples.append(x_here)
            ypix_at_max.append(iy_max)
            used_ix.append(i)

        x_samples = np.asarray(x_samples)
        ypix_at_max = np.asarray(ypix_at_max)

        if x_samples.size < 2:
            raise RuntimeError("Not enough maxima found within the parallelogram to fit a line.")

        # --- Fit mono ≈ a * pixel + b  (same calibration as your original)
        a, b = np.polyfit(ypix_at_max, x_samples, 1)
        calibrated_axis = np.polyval([a, b], np.arange(ny))

        # --- Optional diagnostic plot
        if plot_on:
            plt.figure(figsize=(6, 4))
            # Display Z with axes: x = mono (horizontal), y = pixel (vertical)
            plt.pcolormesh(mono,range(0,Z.shape[1]),Z.T,cmap='Reds',vmin=0,vmax=np.max(Z))
            plt.colorbar(label='Intensity')

            # Draw the two points
            plt.scatter([mono[ind_x1], mono[ind_x2]], [px_y1, px_y2],
                        s=60, c='white', edgecolor='k')

            # Draw center and top/bottom edges
            x_line = np.linspace(mono[ix_start], mono[ix_end], 200)
            y_center = m * x_line + c
            y_top = y_center + half_w
            y_bot = y_center - half_w
            plt.plot(x_line, y_center, 'w--', lw=1.5, color='k',label='initial guess')
            plt.plot(x_line, y_top,    'w-',  lw=1.0, alpha=0.8,color='k')
            plt.plot(x_line, y_bot,    'w-',  lw=1.0, alpha=0.8,color='k')

            # Scatter maxima used for the fit
            plt.scatter(x_samples, ypix_at_max, s=20, c='yellow', edgecolor='k')

            # Plot fitted calibration line (x vs pixel)
            ypix = np.arange(ny)
            plt.plot(np.polyval([a, b], ypix), ypix, 'r-', lw=2,
                     label=f'fit: mono = {a:.6g} * pixel + {b:.6g}')
            plt.xlim(mono[0],mono[-1])
            plt.xlabel('Energy (mono)')
            plt.ylabel('Pixel')
            plt.title(f'Elastic Calibration via Parallelogram (width={width_pixels} px)')
            plt.legend(loc='best')
            plt.tight_layout()
            plt.show()

        details = {
            "x_samples": x_samples,
            "ypix_at_max": ypix_at_max,
            "used_x_indices": np.array(used_ix, dtype=int),
            "center_line_m_c": (m, c),
            "width_pixels": width_pixels,
        }
        return calibrated_axis, (a, b), details
    
    def emi_calibration(self, p1, p2, width_pixels = 10, plot_on = True, use = 'on'):
        if use == 'on':
            mono = self.average['scanvar_on']
            rixs = self.average['axis_svls_on_mean']
        elif use == 'off':
            mono = self.average['scanvar_off']
            rixs = self.average['axis_svls_off_mean']
        else:
            mono = self.average['scanvar']
            rixs = self.average['axis_svls_mean']

        calibrated_axis, (a, b), details = self.elastic_calibrate_from_two_points(
                                    mono,
                                    rixs,
                                    p1, p2,
                                    width_pixels=width_pixels,
                                    plot_on=plot_on
                                 )
        self.average['emi'] = calibrated_axis
        return calibrated_axis, (a, b), details

    def save_avg(self):
        print('saving data')
        runs = self.runs
        output = h5py.File(f'./avg/Run{runs[0]:04d}to{runs[-1]:04d}.h5','w')
        keys = self.average.keys()

        for key in keys:
            output.create_dataset(key,dtype='f',data=self.average[key])

        output.close()


    
