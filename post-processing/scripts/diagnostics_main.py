# Imports.
import os;
import sys;
import pathlib;
import diagnostics;
import IO_utilities as IO;
import gysela_utilities as utils;

# Variables.
sugared_diagnostic_names = {
	"rosenbluth_hinton_mn0": "Rosenbluth Hinton",
	"parameter_scan": "Parameter Scan",
	"psd_mn0": "Spectral Analysis",
	"phixy_mn0": f"$\phi$ (2D)",
	"phixy_mn0_animation": f"$\phi$ (2D), Animation",
	"hovmoller_mn0": "Hovmoller",
	"GAM_phase_lag": "m = 1 vs m = 0 Phase Comparison"
};

# Contextual data.
runtime_data = {
	
	"filename_prefix": None,
	"phi2D_list": None,
	"time_step": None,
	"simulation_directory_path": None
};

# -------------------------------------------------------------------
# --------------------Interface/front-end logic. --------------------
# -------------------------------------------------------------------

def process_filename(suffix):

	prefix = runtime_data.get("filename_prefix");
	return f"{prefix}_{suffix}";

def get_diagnostics():

	diagnostics_path = pathlib.Path(f"{os.getcwd()}/diagnostics");
	# 'stem' retrieves the file-name sans the extension.
	return [file.stem for file in diagnostics_path.glob("*.py")];

def diagnostics_interface():

	if not __name__ == "Main":
		sys.exit();

	print("This script is the main entry point for all post-processing scripts and diagnostics.");
	diagnostics_files = get_diagnostics();

	if not diagnostics_files:

		print("No diagnostics found! Exiting.");
		return;

	directory_path = input("Please enter the path to the simulation output directory: ");
	is_bash_env_var = input("Have you supplied a Bash environmental variable? (y/n) [default y]?: ");

	if IO.is_yes(is_bash_env_var):

		print("Reading the directory path as a Bash environment variable...");
		directory_path = IO.read_bash_env_variable(directory_path);

	print(f"Got {directory_path} as the simulation data directory.");
	print("Validating directory contents...")

	if not validate_simulation_directory(directory_path, is_bash_env_var):

		print("The provided simulation directory is not valid! Exiting.");
		return;

	print("Directory is valid.");
	time_step, data_arrays = IO.fetch_timestep_and_data_arrays(directory_path, is_bash_env_var);
	print_data_properties(time_step, data_arrays);
	input_loop(diagnostics_files);

def input_loop(options_list):

	print_options(options_list);
	answer = input("Select an option: ");
	# TODO:

def print_data_properties(time_step, data_arrays):

	print(f"Got {time_step} for time-step, in code units.");
	print(f"Retrieved {len(data_arrays)} Phi2D data objects.");

def print_options(options_list):

	for index, option in options_list:

		# If no sugared name exists, produce something reasonably human-readable.
		option_name = sugared_diagnostic_names.get(option, option.replace("_", "").title());
		print(f"[{index}] {option_name}.");

	print(f"[{len(options_list) + 1}] Exit.");
	print("-" * 20);

def validate_simulation_directory(directory_path, is_bash_env_var = True):
	# TODO: needs testing
	directory_path = IO.read_bash_env_variable(directory_path) if is_bash_env_var else directory_path;
	master_directory = pathlib.Path(directory_path);
	subdirectories = [object for object in master_directory if object.isdir()];
	return "sp0" in subdirectories;

diagnostics_interface();