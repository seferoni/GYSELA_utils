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
	pretty_print "Copying files from $1 to $2".
	exclusion_list=$(generate_exclusion_list)
	rsync -arzP "$exclusion_list" "$1" "$2";
}

generate_exclusion_list()
{
	exclusion_list="--exclude='rst_files/'"
	echo "$exclusion_list"
}

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