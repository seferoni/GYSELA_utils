import sys;
import h5py;
import numpy as np;
from pathlib import Path;

# Auxiliary functions.
def compile_phi2D_data(h5_files):

	# Sequence/list of 2D arrays, each array a snapshot of the electrostatic potential.
	phi2D_data = [];

	for h5_file in h5_files:
		phi2D_n0 = read_hdf5_file(h5_file);
		phi2D_data.append(phi2D_n0);

	return np.array(phi2D_data);

def fetch_phi2D_filepaths(nominal_path):

	directory_path = Path(nominal_path);

	if not directory_path.is_dir():
		print(f"Error: The given directory '{nominal_path}' could not be resolved.");
		return [];

	h5_files = [file.resolve() for file in directory_path.glob("Phi2D_d*.h5")];
	return sorted(h5_files);

def read_hdf5_file(filepath):
	# TODO: implementation incomplete.
	h5_file = h5py.File(filepath, 'r')
	print(f"{filepath} has been successfully resolved and opened.");
	return h5_file["Phirth_n0"][:];

def fetch_phi2D_data():

	if len(sys.argv) != 2:
		print("Usage: python hdf5_reader.py <absolute_path_to_hdf5_file>");
		print("Aborting.");
		sys.exit(1);

	h5_directory = sys.argv[1];
	h5_files = fetch_phi2D_filepaths(h5_directory);
	
	if len(h5_files) == 0:
		print("No HDF5 files found in the specified directory.");
		print("Aborting.");
		sys.exit(1);

	return compile_phi2D_data(h5_files);