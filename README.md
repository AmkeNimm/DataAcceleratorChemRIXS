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


## Required input files
The pipeline needs two categories of input: **small data files** and **YAML configuration**.
1. **Raw data — "smalldata" HDF5 files** :
Every processing entry point (SmallData, Reduced, Average) expects an HDF5 file whose path contains the substring Run followed by a 4-digit run number (e.g. .../Run0234.h5), the standard labelling of small data files at LCLS. 

The smalldata file is expected to have:

**/intg** — group of integrating detectors (e.g. axis_svls, andor_vls, andor_dir), each with count, a full-frame dataset, timing_sum_eventcodes, per-shot mono encoder, and waveform-detector sums for fim0/fim1/apds/piranha.

**single-shot detectors** (piranha, APDs, fim0/fim1, light status, mono encoder, timing).

**/scan** — present for step scans; contains the scan variable (mono energy, delay, waveplate, etc.), used to auto-detect scantype.
an EPICS archiver group (default key epics_archiver) with monochromator/VLS motor readbacks.

You'll also need a dark/background run in the same format (bgpath) — or a pre-reduced background HDF5 if you point red_bg_path at one in the YAML.

2. **YAML configuration files** (repo root)
These aren't optional side-config — they define the detectors and naming (which HDF5 keys map to which attribute names).

## Overall workflow — src/chemrixs

The package is a layered wrapper around HDF5, with each layer doing one job. Data flows bottom-up on load, and reduction flows top-down on process:
Detector          — thin lazy-loading wrapper around one HDF5 sub-group

   ↑ uses

Integrating / Singleshot   — one instance per detector *category* (e.g. the SVLS detector or a transmission detector), applies
                              countmasking, channel summing, mono/delay axis

   ↑ uses

SmallData          — one HDF5 run file; exposes .integrating / .singleshot
                      via cached_property; auto-detects scantype

   ↑ uses

Reduced            — actual physics: BG subtraction, thresholding, rotation,
                      I0 normalization, on/off splitting, binning by scan
                      variable → saves processed data as proc/Run####.h5

   ↑ uses

Average            — averages several processed runs together, computes
                      PFY, optional emission calibration, energy-transfer
                      conversion, and all plotting (2D maps, PFY, CIE,
                      HERFD, CET) → saves avg/Run####to####.h5


## Step by step:

**Detector (detector.py)** — generic base class. Given an HDF5 group and a data_to_read dict (from the YAML *_dict entries), it attaches each requested field as a cached_property so nothing is actually read off disk until you touch the attribute. Supports dask-array loading for large single-shot waveform data.

**Integrating / Singleshot (integrating.py, singleshot.py)** — instantiate one dynamically-named Detector subclass per configured detector (int_detectors/ss_detectors in the YAML), then:

_Integrating.countmask()_ filters out frames whose shot count doesn't match the expected per-frame count (data integrity check for the integrating cameras), with optional timestamp-sort/roll correction for Andor camera misalignment.
Integrating.get_scanvar() builds the actual mono-energy or delay axis from the raw mono encoder + EPICS premirror pitch, using whichever run-range calibration bracket in mono_calib matches the current run.

_summing_channels()_ collapses multichannel waveform detectors (fim0/fim1/APDs) into a single per-shot intensity, then combines fim0+fim1 into I0.
SmallData (smalldata.py) — opens the run's HDF5, resolves the run number from the filename, loads the config YAML, and exposes .integrating/.singleshot lazily. .scantype is auto-detected: it checks /scan for a known scan-variable key (mono, delay, waveplate, delay_fly), and if absent falls back to checking whether the mono encoder has significant spread (→ mono_fly) or is static.

**Reduced (process.py)** — the actual reduction, given path + bgpath + two YAMLs. On construction it:
Loads or computes the background (dark) for each active detector.

_proc_andorvls() / proc_svls() / proc_andordir()_: subtract background, threshold, and — for the SVLS spectrometer — rotate/crop a tilted 2D spectrum and sum onto 1D, or handle the already-2D case directly.
Normalizes each processed detector by I0 (unless norm=False).
Splits into laser-on/laser-off populations using the configured event codes.

_bin_intdet()_ bins everything against the scan variable, branching on scantype (static / mono,delay step scans / mono_fly,delay_fly fly scans), with optional timing-tool delay correction loaded from proc/leading_edge_{run}.txt for fly-scan delay runs.

_save_dat()_ writes all *_on/*_off/*_mean/*_sum/*_std/scanvar/counts attributes to proc/Run####.h5; save_bg() caches the processed background separately so it isn't recomputed for every run.

**Average (average.py)** — given a list of run numbers, calls Reduced on any that aren't already in proc_path (self-healing — reduction happens on demand), then averages the processed runs (avg_data_count/avg_data, weighting by counts if available), computes PFY, and provides the plotting/analysis surface: 2D SVLS maps (plot_svls2D), 1D PFY traces (plot_svls1D), energy-transfer conversion and plots (plot_svls2D_ET), constant-incident-energy/HERFD/constant-energy-transfer cuts, elastic-line calibration by clicking two points on a parallelogram ROI (elastic_calibrate_from_two_points), and save_avg() → avg/Run####to####.h5.

Output directory convention implied by the code (make sure these exist before running): proc/ (per-run reduced data + timing-tool correction files), avg/ (averaged data), figs/ (saved plots).

_chemrixs.utils_ module is imported throughout (normalise, bin_data, bin_svls, get_PFY, get_CIE/get_HERFD/get_CET, sum_channels, emi2ET, mono_energy, get_premirror_pitch, find_nearest) but isn't included in the published API docs — it's the shared numerical toolkit the other five modules all lean on.

To do analysis several 'pre steps' are needed:

## Calibration
see notebook xx

## Timing Tool Analysis
see notebook './jupyter_notebook/TT_test.ipynb'

From there several runs can easily be run in a few steps as seen in notebook  xx.
All parameters for reduction are defined in xx.yaml

## Run reduction and plot data
examples in './jupyter_notebook'
