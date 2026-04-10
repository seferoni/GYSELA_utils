# Imports.
import numpy as np;
import pandas as pd;
import h5_reader_xr as reader;

# -------------------------------------------------------------------
# -------- -------------------Generic. ------------------------------
# -------------------------------------------------------------------

def slice_at_effective_radius(radial_time_series, effective_radius = 0.7):

	total_radial_size = radial_time_series.sizes["r"] - 1;
	radial_index = round(effective_radius * total_radial_size);
	return radial_time_series[:, radial_index].values;

def generate_time_range_by_series(radial_time_series, dt_diag):

	naive_range = np.arange(len(radial_time_series));
	return naive_range * dt_diag;