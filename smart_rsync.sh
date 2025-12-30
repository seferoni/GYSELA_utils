#!/bin/bash

# Basic variables.
# Because God hates Bash and myself, true is 0 and false is 1... so as to play nice with exit codes.
true=0
false=1

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

is_no()
{
	case "$1" in
		[nN]*)	return $true ;;
		*)		return $false ;;
	esac
}

# Exclusion lists sourced from `recup2nashira.sh`.
# TODO: scrutinise these, please. not all of this immediately makes sense to me
exclude_list1="--exclude='DATA' --exclude='core.*' --exclude='file_list.out'  --exclude='gysela_res.err' --exclude='*.exe' --exclude='*rst.*' --exclude='outofdomain*'"
# exclude_list1 is completely inconsequential, excluding stuff in the realm of kilobytes lol
exclude_list2="--exclude='Phi3D/' --exclude='moment3D/' --exclude='fluxes3D/' --exclude='*3D*.h5'"
# only for simulations that output 3D data. all of my simulations churn out 2D, and... not sure why that's the case
exclude_list3="--exclude='mtm_*.out'"
# why not exclude mtm_trace/ entirely? anyway, this is on the realm of 14 MB which is peanuts
exclude_list4="--exclude='f5D/'"
# also super teeny tiny
exclude_list5="--exclude='moment3D/' --exclude='fluxes3D/'"
# just a repeat of what came before... so these are worthless

# Main script logic.
if [[ $# -ne 1 ]]
then
	pretty_print "Usage: $0 <simulation_directory>"
	exit 1
fi

