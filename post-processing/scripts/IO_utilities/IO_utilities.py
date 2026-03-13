# Imports.
import os;
import h5_reader_xr as reader;

# -------------------------------------------------------------------
# --------------------I/O helper functions. -------------------------
# -------------------------------------------------------------------

def is_yes(answer):

	valid_answers = ["y", "Y", "yes", "Yes", "YES", ""];
	return answer in valid_answers;

def read_bash_env_variable(variable_name):

	return os.environ[variable_name];

def fetch_timestep_and_data_arrays(directory_path, is_dirpath_env_var = True):

	if is_dirpath_env_var:

		directory_path = read_bash_env_variable(directory_path);

	if not os.path.exists(directory_path + "/sp0"):

		raise Exception("The supplied directory is not a valid simulation output directory.");

	time_step = read_timestep(directory_path);
	data_arrays = reader.compile_data_from_directory(directory_path + "/sp0/Phi2D");
	return time_step, data_arrays;

def read_timestep(directory_path):

	time_step = reader.fetch_data_from_h5(directory_path + "/sp0/Phi2D/Phi2D_d00000.h5")["time_step"].values;
	return time_step;