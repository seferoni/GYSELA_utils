# Imports.
import xarray as xr;
from pathlib import Path;

# General utility functions.
def compile_data_from_directory(data_key, nominal_path, to_numpy = False):

	dataset_list = fetch_data_from_directory(nominal_path);
	
	# The onus for input validation is on the user.
	data_arrays = [dataset[data_key] for dataset in dataset_list];

	if to_numpy:
		data_arrays = [data_array.to_numpy() for data_array in data_arrays];

	return data_arrays;

def fetch_data_from_h5(filepath, dimensions = None):

	# If xarray complains (as it is often wont to do), changing the engine can help.
	dataset = xr.open_dataset(filepath, engine = "h5netcdf", phony_dims = "sort");

	if dimensions is not None:
		# We match each `phony_dim` by comparing array sizes.
		dataset = dataset.rename(phony_dim_0 = dimensions[0], phony_dim_1 = dimensions[1], phony_dim_2 = dimensions[2]).load();

	# Discard size-1 dimensions.
	dataset = dataset.squeeze();
	return dataset;

def fetch_phi2D_data_from_h5(filepath, dataset_key = "Phirth_n0"):

	return fetch_data_from_h5(filepath, dimensions = ["zeta", "r", "theta"])[dataset_key];

def fetch_f2D_data_from_h5(filepath, dataset_key = "frvpar_passing"):

	return fetch_data_from_h5(filepath, dimensions = ["zeta", "r", "vpar"])[dataset_key];

def fetch_phi2D_filepaths(nominal_path):

	directory_path = Path(nominal_path);

	if not directory_path.is_dir():
		print(f"The given directory '{nominal_path}' could not be resolved.");
		return [];

	h5_files = [file.resolve() for file in directory_path.glob("Phi2D_d*.h5")];
	return sorted(h5_files);

def fetch_data_from_directory(nominal_path):
	
	compiled_data = [];
	h5_files = fetch_phi2D_filepaths(nominal_path);

	if not h5_files:

		print(f"No h5 files could be retrieved from {nominal_path}.");
		return compiled_data;

	for h5_file in h5_files:

		data = fetch_data_from_h5(h5_file);
		compiled_data.append(data);

	return compiled_data;

# Recall that we can source the names of individual datasets via HDFView or similar.
def fetch_delta_t(directory_path):
	
	return fetch_data_from_h5(f"{directory_path}/sp0/Phi2D/Phi2D_d00000.h5")["deltat"].values;

def fetch_phi2D_data(directory_path, dataset = "Phirth_n0"):

	return compile_data_from_directory(dataset, f"{directory_path}/sp0/Phi2D");

def fetch_f2D_data(directory_path, dataset = "frvpar_passing"):

	return compile_data_from_directory(dataset, f"{directory_path}/sp0/f2D");