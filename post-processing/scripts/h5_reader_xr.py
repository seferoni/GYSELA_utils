# Imports.
import xarray as xr;
from pathlib import Path;
from joblib import Parallel, delayed;

# General utility functions.
def compile_data_from_directory(data_key, nominal_path, file_type, dimensions = None, file_limit = None, parallelise = False):

	operation = fetch_data_from_directory if not parallelise else fetch_data_from_directory_parallelised;
	dataset_list = operation(nominal_path, file_type, dimensions, file_limit);
	
	if data_key is None:
		return dataset_list;

	# The onus for input validation is on the user.
	data_arrays = [dataset[data_key] for dataset in dataset_list];
	return data_arrays;

def fetch_data_from_h5(filepath, dimensions = None, group = None):

	# If xarray complains (as it is often wont to do), changing the `engine` kwarg can help.
	dataset = xr.open_dataset(filepath, engine = "h5netcdf", phony_dims = "sort", group = group);

	if dimensions is None:
		# Discard size-1 dimensions.
		return dataset.load().squeeze();

	for index, new_name in enumerate(dimensions):

		phony_dimension_index = f"phony_dim_{index}"
		dataset = dataset.rename({phony_dimension_index : new_name});

	return dataset.load().squeeze();

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

	if file_limit is not None: h5_files = h5_files[:file_limit];

	for h5_file in h5_files:

		data = fetch_data_from_h5(h5_file, dimensions);
		compiled_data.append(data);

		if len(compiled_data) % 1000 == 0:
			print(f"Compiled data from {len(compiled_data)} files...");
	
	print("Finished compiling data from all files in the directory.");
	return compiled_data;

def fetch_data_from_directory_parallelised(nominal_path, file_type, dimensions = None, file_limit = None, n_jobs = 16, prefer = "processes"):

	h5_files = fetch_filepaths(nominal_path, file_type);

	if not h5_files:
		print(f"No h5 files could be retrieved from {nominal_path}.");
		return [];

	if file_limit is not None: h5_files = h5_files[:file_limit];

	print(f"Found {len(h5_files)} files in the directory. Loading with {n_jobs} workers...");

	compiled_data = Parallel(n_jobs = n_jobs, prefer = prefer, backend = "loky", verbose = 1)(
		delayed(fetch_data_from_h5)(h5_file, dimensions) for h5_file in h5_files
	);

	print("Finished compiling data from all files in the directory.");
	return compiled_data;

# Recall that we can source the names of individual datasets via HDFView or similar.
def fetch_jacobian(directory_path, path_suffix = "sp0/init_state/magnet_config_r000.h5"):

	dataset = fetch_data_from_h5(f"{directory_path}/{path_suffix}");
	return {
		"naive": dataset["jacob_space"].rename({"phony_dim_0": "theta", "phony_dim_1": "r"}),
		"integrated_over_theta": dataset["intdtheta_Js"].rename({"phony_dim_1": "r"}),
		"integrated_over_theta_and_phi": dataset["intdthetadphi_Js"].rename({"phony_dim_1": "r"}),
	};

def fetch_dt_diag(directory_path, path_suffix = "sp0/init_state/data_r000.h5"):

	return fetch_data_from_h5(f"{directory_path}/{path_suffix}", group = "DATA/ALGORITHM")["dt_diag"].values;

def fetch_delta_t(directory_path, path_suffix = "sp0/Phi2D/Phi2D_d00000.h5"):

	return fetch_data_from_h5(f"{directory_path}/{path_suffix}")["deltat"].values;

def fetch_phi2D_data(directory_path, dataset = "Phirth", dimensions = ["zeta", "r", "theta"], file_limit = None, parallelise = False):

	return compile_data_from_directory(dataset, f"{directory_path}/sp0/Phi2D", "Phi2D", dimensions, file_limit, parallelise);

def fetch_f2D_data(directory_path, dataset = "frvpar_passing", dimensions = ["zeta", "r", "vpar"], file_limit = None, parallelise = False):

	return compile_data_from_directory(dataset, f"{directory_path}/sp0/f2D", "f2D", dimensions, file_limit, parallelise);

def fetch_rprof_data(directory_path, dataset, dimensions = ["r"], file_limit = None, parallelise = False):

	return compile_data_from_directory(dataset, f"{directory_path}/sp0/rprof", "rprof_GC", dimensions, file_limit, parallelise);

def fetch_conservation_laws_data(directory_path, dataset, dimensions = None, file_limit = None, parallelise = False):

	return compile_data_from_directory(dataset, f"{directory_path}/sp0/conservation_laws", "conservation_laws", dimensions, file_limit, parallelise);