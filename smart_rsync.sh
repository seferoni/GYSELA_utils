#!/bin/bash

# Basic variables.
# Because God hates Bash and myself, true is 0 and false is 1... so as to play nice with exit codes.
readonly true=0
readonly false=1

# Basic functions.
pretty_print()
{
	printf "\n%s\n" "$1"
}

is_yes()
{
	case "$1" in
		[yY]*)	return $true ;;
		*)		return $false ;;
	esac
}

# Bespoke helper functions.
check_and_set_target_directory()
{
	if [[ ! -v SMARTRSYNCPATH ]]
	then 
		pretty_print "The environment variable SMARTRSYNCPATH is not defined. Please either define it or specify a target directory."
		echo -n "Would you like to specify a target directory now? (y/n)"
		read -r answer

		if is_yes "$answer"
		then 
			pretty_print "Please specify the target directory:"
			read -r answer

			if [[ ! -d "$answer" ]] #TODO: this will not work for remote directories. use rsync's dry run instead
			then
				echo "The specified directory '$answer' does not exist. Aborting."
				return $false
			fi

			export SMARTRSYNCPATH="$answer"
			pretty_print "Target directory defined as $SMARTRSYNCPATH. Note that this is only set for the current session."
			return $true
		fi

		pretty_print "Aborting copy. Smell ya later, nerd."
		return $false
	fi

	return $true
}

compare_metadata_and_copy()
{
	local source_directory="$1"
	local metadata_0_creationdate
	local metadata_1_creationdate
	local exclusion_list
	
	metadata_0_creationdate="$(stat -c %Y "$source_directory/sp0/rst_files/metadata.n0.h5")"
	metadata_1_creationdate="$(stat -c %Y "$source_directory/sp0/rst_files/metadata.n1.h5")"

	if [[ $metadata_0_creationdate -gt $metadata_1_creationdate ]]
	then
		pretty_print "n0 is newer than n1. Excluding n1 files."
		exclusion_list=$(generate_exclusion_list "n1")
	else
		pretty_print "n1 is newer than n0. Excluding n0 files."
		exclusion_list=$(generate_exclusion_list "n0")
	fi

	pretty_print "Copying files from $source_directory to $SMARTRSYNCPATH, excluding older restart data."
	rsync -arzP "$exclusion_list" "$source_directory" "$SMARTRSYNCPATH"
	echo "Copy complete. Buh-bye!"
}

generate_exclusion_list()
{
	local rst_exclusion_number="$1"
	local exclusion_list=""
	exclusion_list+="--exclude=metadata.${rst_exclusion_number}.h5"
	exclusion_list+=" --exclude=.${rst_exclusion_number}.*h5"
	echo "$exclusion_list"
}

is_eligible_for_restart_culling()
{
	local source_directory="$1"

	if [[ ! -f "$source_directory/sp0/rst_files/metadata.n0.h5" ]]
	then return $false
	fi

	if [[ ! -f "$source_directory/sp0/rst_files/metadata.n1.h5" ]]
	then return $false
	fi

	return $true
}

copy_files_naively()
{
	pretty_print "Copying files naively from $1 to $SMARTRSYNCPATH".
	rsync -arzP "$1" "$SMARTRSYNCPATH"
}

# Main script logic.
if [[ $# -ne 1 ]]
then
	pretty_print "This is a script to copy simulation data folders while excluding older restart data."
	echo "The target directory can be specified via the environment variable SMARTRSYNCPATH."
	echo "Usage: ./smart_rsync.sh <simulation_directory>"
	exit 1
fi

if ! check_and_set_target_directory
then
	exit 1
fi

if is_eligible_for_restart_culling "$1"
then
	compare_metadata_and_copy "$1"
	exit 0
fi

copy_files_naively "$1"
exit 0