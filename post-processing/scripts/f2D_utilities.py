# Imports.
import numpy as np;
import xarray as xr;
import pandas as pd;
import h5_reader_xr as reader;
import os;
import glob;

def calculate_stride(delta_t, dt_diag):

	# The logic is this: for a dt_diag of 50, and a delta_t of 25, we have a stride of 2.
	# Stride is also the diagnostic interval; for every two simulation time-steps (50 code units), we have one Phi2D sample.
	# This still retains the normalisation interred within GYSELA itself.
	return dt_diag / delta_t;

def compute_delta_f_vpar(f2D_list):
	# Convert from f(r, vpar) to delta_f(vpar).
	maxwellian = f2D_list[0];
	delta_f_vpar_time = [];
	
	for perturbed_distribution in f2D_list:

		delta_f = perturbed_distribution - maxwellian;
		delta_f_v = delta_f.mean(dim="r");
		delta_f_vpar_time.append(delta_f_v.values);
	
	delta_f_vpar_time = np.array(delta_f_vpar_time);
	vpar = f2D_list[0]["vpar"].values;
	return vpar, delta_f_vpar_time;
