# Imports.
import xarray as xr;
from pathlib import Path;

# General utility functions.
def get_input_file_path(directory_path):

	directory_path = Path(directory_path);
	# The filename is 'input.' followed by the name of the folder
	input_filename = f"input.{directory_path.name}";
	full_path = directory_path / input_filename;
	
	if not full_path.exists():
		raise FileNotFoundError(f"Could not find input file at: {full_path}.");
		
	return full_path;

def fetch_parameter_value(directory_path, parameter):

	input_file_path = get_input_file_path(directory_path);
	disregard_line = lambda line: not line or line.startswith(("#", "!"));
	value = None;
	file = open(input_file_path, mode = "r");
		
	for line in file:

		clean_line = line.strip();
		
		if disregard_line(clean_line):
			continue;
	
		if parameter not in clean_line:
			continue;
	
		# Splits the string along =, producing a list containing two strings.
		string_parts = clean_line.split("=");

		if string_parts[0].strip() != parameter:
			continue;
		
		print(f"Found line: \"{clean_line}\".");
		print("Isolating value...");
		value_string = string_parts[1].split("!")[0].strip();

		try:

			value = int(value_string);
			print(f"Success: Got value {value}.");
			break;
		
		except ValueError:

			print(f"Error: found {parameter} but value {value_string} cannot be converted into an integer.");
			break;
	
		except Exception:

			print(f"Error: unhandled exception.");
			break;

	file.close();
	return value;