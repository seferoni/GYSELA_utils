#!/bin/bash
# I hate Bash. It's ugly. I miss Powershell.

# Main script logic.
if [[ $# -lt 1 ]]
then
	printf "This script removes GYSELA simulation directories and all associated output files."
	printf "Usage: ./rml_rev [SIMULATION_DIRECTORY]"
	printf "If no argument is provided, all simulation directories in the current folder will be removed."

	simulation_directories=()
	mapfile -d '' simulation_directories < <(find . -maxdepth 1 \( -type d -o -type l \) -name 'D*' -print0);
	directory_count=${#simulation_directories[@]}

	if [[ $directory_count -eq 0 ]]
	then
		echo "No simulation directories found in the current folder. Aborting."
		exit
	fi

	echo "Found $directory_count simulation directories."
	echo -n "Would you like to remove them and their associated logs? (y/n)"
	read -r answer

	if [[ "$answer" != "y" ]]
	then
		echo "Aborting. See ya, chump!"
		exit
	fi


	# TODO: fun stuff here.
fi

# TODO: still need a way to identify associated logs and debug cmd. also need logic for when an arg is passed, but this is easy peasy
