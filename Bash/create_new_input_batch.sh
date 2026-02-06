#!/bin/bash
# TODO:
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
cull_obsolete_entries()
{
	local input_file="$1"
	local patterns=(
		"^[[:blank:]]*Vlasov Scheme[[:blank:]]*=[[:blank:]]*[^![:blank:]].*"
	)

	pretty_print "Culling obsolete entries..."
	for pattern in "${patterns[@]}"
	do
		if grep -q "$pattern" "$input_file"
		then
			sed -i "/$pattern/d" "$input_file"
		fi
	done
	echo "Culled all obsolete entries."
}

match_input_to_dictionary()
{
	local input="$1"
	generate_parameter_dictionary

	if [[ -v "parameter_dictionary[$input]" ]]
	then 
		echo "${parameter_dictionary[$input]}"
		return $true
	fi

	echo "$input"
	return $false
}

set_target_directory()
{
	local answer
	pretty_print_query "Please specify the absolute path of the target file."
	read -r answer

	if [[ -z "$answer" ]]
	then
		echo "No input received. Aborting."
		return $false
	fi

	export INPUTFILEPATH="$answer"
	echo "Target file defined as $INPUTFILEPATH. Note that this is only set for the current session."
	echo -n "Would you like to proceed? (Y/n)"
	read -r answer

	if is_yes "$answer"
	then 
		return $true
	fi

	echo "Aborting. Buh-bye!"
	return $false
}

generate_parameter_dictionary()
{
	# The -A flag defines an associative array, and the `-g` flag makes it a global variable.
	declare -gA parameter_dictionary=(
		["restarts"]="NB_RESTART"
		["jobname"]="JOBNAME"
		["time"]="TIME"
		["q"]="q_param1"
		["tau"]="tau0"
		["geometry"]="magnet_strategy"
	)
}