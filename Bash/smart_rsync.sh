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
			export SMARTRSYNCPATH="$answer"
			pretty_print "Target directory defined as $SMARTRSYNCPATH. Note that this is only set for the current session."
			return $true
		fi

		pretty_print "Aborting copy. Smell ya later, nerd."
		return $false
	fi

	return $true
}

copy_files()
{
	pretty_print "Copying files from $1 to $SMARTRSYNCPATH".
	exclusion_list=$(generate_exclusion_list)
	cmd="rsync -arzP $1 $SMARTRSYNCPATH"
	echo "$cmd"
	eval "$cmd"
}

generate_exclusion_list()
{
	exclusion_list="--exclude='rst_files/'"
	echo "$exclusion_list"
}

# Main script logic.
if [[ $# -ne 1 ]]
then
	pretty_print "This is a script to copy simulation data folders while excluding restart data."
	echo "The target directory can be specified via the environment variable SMARTRSYNCPATH."
	echo "Usage: ./smart_rsync.sh <simulation_directory>"
	exit 1
fi

if ! check_and_set_target_directory
then
	exit 1
fi

copy_files "$1"
exit 0