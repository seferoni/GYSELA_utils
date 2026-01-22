import h5py
import numpy as np

def read_user_filepath():
	filepath = input("Please enter the absolute path to the HDF5 file: ")

	if (filepath is None) or (filepath.strip() == ""):
		print("Aborting.")
		exit(1)

	return filepath

def validate_filepath(filepath):
	try:
		h5py.File(filepath, 'r')
	except FileNotFoundError:
		print(f"Error: The given path '{filepath}' could not be resolved.")
		return False
	
	return True

filename = read_user_filepath()
bailout = 10

while not validate_filepath(filename) and bailout > 0:
	filename = read_user_filepath()
	bailout -= 1