#!/bin/bash
# TODO: need to figure out overall process flow. shouldn't be too diff from the single file variant

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

define_input_path()
{
	local answer
	pretty_print_query "Would you like to specify an template file path manually? (Y/n)"
	read -r answer

	if is_yes "$answer"
	then 
		set_target_directory
		return $? # Returns the last retained exit code.
	fi

	if [[ ! -v BATCHINPUTFILEPATH ]]
	then
		echo "The environment variable BATCHINPUTFILEPATH is not defined. Aborting."
		return $false
	fi

	echo "BATCHINPUTFILEPATH found: $BATCHINPUTFILEPATH."
	return $true
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

	export BATCHINPUTFILEPATH="$answer"
	echo "Target file defined as $BATCHINPUTFILEPATH. Note that this is only set for the current session."
	echo -n "Would you like to proceed? (Y/n)"
	read -r answer

	if is_yes "$answer"
	then 
		return $true
	fi

	echo "Aborting. Buh-bye!"
	return $false
}

generate_input_file_copies()
{
	local filename_prefix="$1"
	local parameter_alias="$2"
	local starting_value="$3"
	local end_value="$4"
	local interval_size="$5"
	local queue_for_simulation="$6"

	for value in $(seq "$starting_value" "$interval_size" "$end_value")
	do
		local filename="${filename_prefix}_${value}"
		pretty_print "Generating ${filename}..."

		rsync -arzP "$BATCHINPUTFILEPATH" "./$filename"
		cull_obsolete_entries "$filename"
		modify_input_parameter "$filename" "jobname" "$filename"
		modify_input_parameter "$filename" "$parameter_alias" "$value"

		if is_yes "$queue_for_simulation"
		then
			queue_for_simulation "$filename"
		fi

	done
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

modify_input_parameter()
{
	local input_file="$1"
	local parameter_alias="$2"
	local value="$3"

	local original_pattern="^([[:blank:]]*${parameter}[[:blank:]]*=[[:blank:]]*)[^![:blank:]].*"
	local parameter
	parameter=$(match_input_to_dictionary "$parameter_alias")

	# Uppercase `E` permits extended regex.
	if grep -qE "$original_pattern" "$input_file"
	then
		# NB: `\` and `|` are equivalent delimiter characters.
		sed -i -E "s|${original_pattern}|\1$value ! Modified by create_new_input_file.sh.|" "$input_file"
		return $true
	fi
	
	echo "Could not find specified parameter '$parameter'."
	return $false
}

query_input_parameters()
{
	pretty_print_query "Please specify the following."
	read -rp "Filename prefix: " filename_prefix
	read -rp "Modified simulation parameter: " parameter
	read -rp "Starting value: " starting_value
	read -rp "End value: " end_value
	read -rp "Interval size: " interval_size
	read -rp "Queue for simulation when done (y/n): " queue_for_simulation
	generate_input_file_copies "$filename_prefix" "$parameter" "$starting_value" "$end_value" "$interval_size" "$queue_for_simulation"
}

queue_for_simulation()
{
	local input_file="$1"
	echo "Queueing $input_file as a GYSELA job."
	./subgys "$input_file"
	return $true
}

# Main script logic.
if [[ $# -ne 0 ]]
then
	pretty_print "This is a script to quickly create a new input file for GYSELA simulations within this script's directory."
	echo "This script should be placed within the \wk directory."
	echo "The target file can be specified via the environment variable BATCHINPUTFILEPATH."
	exit 1
fi

if ! define_input_path
then
	exit 1
fi

query_input_parameters
exit 0