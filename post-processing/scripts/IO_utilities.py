# TODO: NB: still under construction.
# Imports.
import os;
import h5_reader_xr as reader;
import matplotlib.pyplot as plt;
from pathlib import Path;

# -------------------------------------------------------------------
# --------------------I/O helper functions. -------------------------
# -------------------------------------------------------------------

def save_figure(filename):

	# Takes us to the GYSELA_utils directory.
	root_path = Path(__file__).resolve().parent.parent.parent;
	output_path = f"{root_path}/output/{filename}";
	plt.savefig(output_path);

def is_yes(answer):

	valid_answers = ["y", "Y", "yes", "Yes", "YES", "FO SHO", "OUI", "OINK OINK", "HALLELUJAH", ""];
	return answer in valid_answers;

def read_bash_env_variable(variable_name):

	return os.environ[variable_name];