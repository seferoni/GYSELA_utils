#!/bin/bash

# Basic variables.
# Because God hates Bash and myself, true is 0 and false is 1... so as to play nice with exit codes.
readonly true=0
readonly false=1
readonly green="\033[0;32m"
readonly end_colour="\033[0m"

# Basic functions.
pretty_print()
{
	printf "\n%b\n" "$1"
}

pretty_print_query()
{
	printf "\n%b" "${green}$1${end_colour}"
}

is_yes()
{
	case "$1" in
		[yY]*|"")	return $true ;;
		*)		return $false ;;
	esac
}

# Bespoke helper functions.
copy_files()
{
	local source="$1"
	local destination="$2"

	# Make directory in-case it doesn't already exist.
	mkdir -p "$destination"

	pretty_print "Copying files from $source to $destination".
	generate_exclusion_list
	rsync -arzP "${EXCLUSIONS[@]}" "$source" "$destination"
}

copy_all_simulation_dirs()
{
	local target_directory="$1"
	local simulation_links=()
	mapfile -d '' simulation_links < <(find . -maxdepth 1 -type l -name 'DN_*' -print0)
	local link_count=${#simulation_links[@]}

	if [[ $link_count -eq 0 ]]
	then
		pretty_print "No simulation links found in /wk!"
		return
	fi

	pretty_print "Copying all folders with simulation links."
	echo "Source directory: $NSCCPROJECTS."
	echo "Target directory: $target_directory."
	echo "Found $link_count simulation links."
	
	for link in "${simulation_links[@]}"
	do
		local simulation_directory
		simulation_directory=$(readlink -f "$link")

		if [[ -d "$simulation_directory" ]]
		then
			echo "Copying directory: $simulation_directory..."
			copy_files "$simulation_directory" "$target_directory"
		fi
	done
}

generate_exclusion_list() 
{
	EXCLUSIONS=(
		"--exclude=rst_files/"
		"--exclude=conservation_laws/"
		"--exclude=POPE/"
		"--exclude=rprof/"
		"--exclude=/mtm_trace/"
		"--exclude=init_state/"
		"--exclude=f2d/"
		"--exclude=f5d/"
		"--exclude=fluxes3D/"
		"--exclude=*.tmp"
	)
}

if [[ $# -eq 1 ]]
then
	pretty_print "Specified target directory: $1"

	if [[ ! -v NSCCPROJECTS ]]
	then
		echo "The environment variable NSCCPROJECTS is not defined. Aborting."
		exit 1
	fi

	pretty_print_query "Would you like to copy over all simulation directories to the specified directory? (Y/n)"
	read -r answer

	if ! is_yes "$answer"
	then
		echo "Aborting."
		exit 1
	fi

	copy_all_simulation_dirs "$1"
fi

# Main script logic.
if [[ $# -ne 2 ]]
then
	pretty_print "This is a script to copy simulation data folders while excluding restart data."
	echo "The target directory can be specified via the environment variable SMARTRSYNCPATH."
	echo "Usage: ./smart_rsync.sh <simulation_directory> <target_directory>"
	exit 1
fi

copy_files "$1" "$2"
exit 0