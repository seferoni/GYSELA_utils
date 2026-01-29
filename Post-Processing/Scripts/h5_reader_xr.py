import xarray as xr

def fetch_data_from_h5(filepath):

	dataset = xr.open_dataset(filepath);
	# NB: As per the input file, Nr = 63, Ntheta = 128, Nphi = 8.
	# We match each `phony_dim` by comparing array sizes.
	dataset = dataset.rename(phony_dim_0 = "zeta", phony_dim_1 = "r", phony_dim_2 = "theta").load();
	# Discard size-1 dimensions.
	dataset = dataset.squeeze();
	return dataset;