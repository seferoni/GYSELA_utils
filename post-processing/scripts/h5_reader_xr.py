# Imports.
import xarray as xr;
from pathlib import Path;

# General utility functions.
def compile_data_from_directory(data_key, nominal_path, file_type, dimensions = None, file_limit = None, to_numpy = False):

	dataset_list = fetch_data_from_directory(nominal_path, file_type, dimensions, file_limit);
	
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

def fetch_filepaths(nominal_path, file_type):

	directory_path = Path(nominal_path);

	if not directory_path.is_dir():
		print(f"The given directory '{nominal_path}' could not be resolved.");
		return [];

	h5_files = [file.resolve() for file in directory_path.glob(f"{file_type}_d*.h5")];
	return sorted(h5_files);

def fetch_data_from_directory(nominal_path, file_type, dimensions = None, file_limit = None):
	
	compiled_data = [];
	# By this point, h5_files is already sorted.
	h5_files = fetch_filepaths(nominal_path, file_type);

	if not h5_files:

		print(f"No h5 files could be retrieved from {nominal_path}.");
		return compiled_data;

	print(f"Found {len(h5_files)} files in the directory. Beginning compilation...");

	for h5_file in h5_files:

		data = fetch_data_from_h5(h5_file, dimensions);
		compiled_data.append(data);

		if len(compiled_data) % 1000 == 0:
			print(f"Compiled data from {len(compiled_data)} files...");
	
		if file_limit is not None and len(compiled_data) >= file_limit:
			print(f"File limit of {file_limit} reached. Stopping compilation.");
			break;
	
	print("Finished compiling data from all files in the directory.");
	return compiled_data;

# Recall that we can source the names of individual datasets via HDFView or similar.
def fetch_delta_t(directory_path):
	
	return fetch_data_from_h5(f"{directory_path}/sp0/Phi2D/Phi2D_d00000.h5")["deltat"].values;

def fetch_phi2D_data(directory_path, dataset = "Phirth_n0", dimensions = ["zeta", "r", "theta"], file_limit = None):

	return compile_data_from_directory(dataset, f"{directory_path}/sp0/Phi2D", "Phi2D", dimensions, file_limit);

def fetch_f2D_data(directory_path, dataset = "frvpar_passing", dimensions = ["zeta", "r", "vpar"], file_limit = None):

	return compile_data_from_directory(dataset, f"{directory_path}/sp0/f2D", "f2D", dimensions, file_limit);