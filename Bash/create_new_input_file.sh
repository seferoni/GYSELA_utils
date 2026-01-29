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
	printf "\n%s\n" "$1"
}

pretty_print_query()
{
	pretty_print "${green}$1${end_colour}"
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

define_input_path()
{
	local answer
	pretty_print_query -n "Would you like to specify an template file path manually? (Y/n)"
	read -r answer

	if [[ -z "$answer" ]]
	then
		echo "No input received. Aborting."
		return $false
	fi

	if is_yes "$answer"
	then 
		set_target_directory
		return $? # Returns the last retained exit code.
	fi

	if [[ ! -v INPUTFILEPATH ]]
	then
		echo "The environment variable INPUTFILEPATH is not defined. Aborting."
		return $false
	fi

	echo "INPUTFILEPATH found: $INPUTFILEPATH."
	return $true
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
		["time"]="TIME"
		["q"]="q_param1"
		["tau"]="tau0"
		["geometry"]="magnet_strategy"
	)
}

generate_input_file_copy()
{
	echo "Generating a new input file based on the template at $INPUTFILEPATH."
	pretty_print_query "Please name the new input file (default: 'my_cool_input_file'):"
	read -r filename

	if [[ -z "$filename" ]]
	then
		filename="my_cool_input_file"
	fi

	rsync -arzP "$INPUTFILEPATH" "./$filename"
	echo "New input file created: ./$filename".
	cull_obsolete_entries "$filename"
	modify_input_parameters "$filename"
	queue_for_simulation "$filename"
}

match_input_to_dictionary()
{
	local input="$1"
	generate_parameter_dictionary

	if [[ -v "parameter_dictionary[$input]" ]]
	then 
		echo "${parameter_dictionary[$key]}"
		return $true
	fi

	echo "$input"
	return $false
}

modify_input_parameters()
{
	local input_file="$1"
	local answer user_key parameter value 

	# `basename` strips the directory path from the filename. Not strictly necessary here, but keeps the code versatile.
	pretty_print_query "Modify input parameters in $(basename "$input_file") now? (Y/n)"
	read -r answer

	if ! is_yes "$answer"
	then 
		pretty_print "Concluding input parameter modification."
		return $true
	fi

	echo "Specify the parameter (either a recognised alias or an exact name):"
	read -r user_key

	parameter=$(match_input_to_dictionary "$user_key")

	echo "Specify the new value for '$parameter':"
	read -r value

	local original_pattern="^([[:blank:]]*${parameter}[[:blank:]]*=[[:blank:]]*)[^![:blank:]].*"
	local new_line="${parameter} = ${value} ! Modified by create_new_input_file.sh."

	# Uppercase `E` permits extended regex.
	if grep -qE "$original_pattern" "$input_file"
	then
		# NB: `\` and `|` are equivalent delimiter characters.
		sed -i -e "s|${original_pattern}|\1{$new_line}|" "$input_file"
		echo "'$parameter' has been updated to '$value'."
	else 
		echo "Could not find specified parameter '$parameter'. Skipping."
	fi

	modify_input_parameters "$input_file"
}

queue_for_simulation()
{
	local input_file="$1"
	local answer
	pretty_print_query "Would you like to queue this simulation file as a GYSELA job? (Y/n)"
	read -r answer

	if ! is_yes answer
	then
		echo "Skipping simulation file queueing."
		return $true
	fi

	./subgys "$input_file"
	echo "Queueing $input_file as a GYSELA job."
	return $true
}

# Main script logic.
if [[ $# -ne 0 ]]
then
	pretty_print "This is a script to quickly create a new input file for GYSELA simulations within this script's directory."
	echo "This script should be placed within the \wk directory."
	echo "The target file can be specified via the environment variable INPUTFILEPATH."
	exit 1
fi

if ! define_input_path
then
	exit 1
fi

generate_input_file_copy
exit 0