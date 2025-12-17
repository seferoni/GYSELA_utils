#!/bin/bash

function identify_simulation_directories () {
	simulation_directories=($(find . -maxdepth 1 \( -type d -o -type l \) -name 'D*' -printf '%f\n')) # TODO: revise
	return "${simulation_directories[@]}";
}


# TODO: still need a way to identify associated logs. also need logic for when an arg is passed, but this is easy peasy
if [[ $# -lt 1 ]]
then
	echo "This script removes GYSELA simulation directories, associated symbolic links, and all associated logs from the current folder."
	echo "Usage: ./rml_rev [SIMULATION_DIRECTORY]"
	echo "If no argument is provided, all simulation directories in the current folder will be removed."

	simulation_directories=($(identify_simulation_directories))
	directory_count=${#simulation_directories[@]}
	echo "Found $directory_count simulation directories."
	echo -n "Would you like to remove them and their associated logs? (y/n)"
	read -r answer

	if [[ "$answer" != "y" ]]
	then
		echo "Aborting. Smell ya later, nerd."
		exit
	fi
	
	# TODO: fun stuff here.
fi