import xarray as xr
from pathlib import Path

def fetch_data_from_h5(filepath):

	dataset = xr.open_dataset(filepath);
	# NB: As per the input file, Nr = 63, Ntheta = 128, Nphi = 8.
	# We match each `phony_dim` by comparing array sizes.
	dataset = dataset.rename(phony_dim_0 = "zeta", phony_dim_1 = "r", phony_dim_2 = "theta").load();
	# Discard size-1 dimensions.
	dataset = dataset.squeeze();
	return dataset;

def fetch_phi2D_filepaths(nominal_path):

	directory_path = Path(nominal_path);

	if not directory_path.is_dir(directory_path):
		print(f"The given directory '{nominal_path}' could not be resolved.");
		return [];

	h5_files = [file.resolve() for file in directory_path.glob("Phi2D_d*.h5")];
	return sorted(h5_files);

def fetch_data_from_directory(nominal_path):
	
	compiled_data = [];
	h5_files = fetch_phi2D_filepaths(nominal_path);

	if (len(h5_files) == 0):
		print(f"Error: no h5 files could be retrieved from {nominal_path}.");
		return compiled_data;

	for h5_file in h5_files:
		data = fetch_data_from_h5(h5_file);
		compiled_data.append(data);

	return compiled_data;