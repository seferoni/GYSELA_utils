# Imports.
import os;
import IO_utilities as IO;
import gysela_utilities as utils;

# Variables.
options = {
	# TODO:
};

# -------------------------------------------------------------------
# --------------------Interface/front-end. --------------------------
# -------------------------------------------------------------------

def diagnostics_interface():

	print("This script is the main entry point for all post-processing scripts and diagnostics.");
	is_bash_env_var = input("Would you like to supply the simulation directory path as a Bash environment variable? (y/n) [default y]?: ");

	if IO.is_yes(is_bash_env_var):

		print("The simulation output directory path will be read as a Bash environment variable.");

	directory_path = input("Please enter the path to the simulation output directory.");
	time_step, data_arrays = IO.fetch_timestep_and_data_arrays(directory_path, is_bash_env_var);

def print_options():
	# TODO: