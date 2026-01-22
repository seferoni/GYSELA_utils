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
define_input_path()
{
	echo -n "Would you like to specify an template file path manually? (y/n)"
	read -r answer

	if [[ -z "$answer" ]]
	then
		pretty_print "No input received. Aborting."
		return $false
	fi

	if is_yes "$answer"
	then 
		set_target_directory
		return $? # Returns the last retained exit code.
	fi

	if [[ ! -v INPUTFILEPATH ]]
	then
		pretty_print "The environment variable INPUTFILEPATH is not defined. Aborting."
		return $false
	fi

	echo "INPUTFILEPATH found: $INPUTFILEPATH."
	return $true
}


set_target_directory()
{
	pretty_print "Please specify the absolute path of the target file."
	read -r answer

	if [[ -z "$answer" ]]
	then
		echo "No input received. Aborting."
		return $false
	fi

	export INPUTFILEPATH="$answer"
	echo "Target file defined as $INPUTFILEPATH. Note that this is only set for the current session."
	echo -n "Would you like to proceed? (y/n)"
	read -r answer

	if is_yes "$answer"
	then 
		return $true
	fi

	echo "Aborting. Buh-bye!"
	return $false
}

generate_input_file_copy()
{
	pretty_print "Generating a new input file based on the template at $INPUTFILEPATH."
	echo "Please name the new input file (default: 'my_cool_input_file'):"
	read -r filename

	if [[ -z "$filename" ]]
	then
		filename="my_cool_input_file"
	fi

	rsync -arzP "$INPUTFILEPATH" "./$filename"
	echo "New input file created: ./$filename".
	echo "Buh-bye!"
	modify_input_parameters $filename
}

modify_input_parameters()
{
	input_file="$1"
	pretty_print "Would you like to modify any (additional) input parameters in $input_file now? (y/n)"
	read -r answer

	if ! is_yes "$answer"
	then 
		pretty_print "Concluding input parameter modification."
		return $true
	fi

	local parameter
	local value
	echo "Please specify the parameter you would like to modify (as it appears in the input file):"
	read -r parameter
	echo "Please specify the new value for '$parameter':"
	read -r value

	local original_pattern="^[[:blank:]]*${parameter}[[:blank:]]*=[[:blank:]]*[^![:blank:]].*"
	local new_line="${parameter} = ${value} ! Modified by create_new_input_file.sh!"
	sed -i -e "s/$original_pattern/$new_line/" "$input_file"
	echo "Parameter '$parameter' updated to value '$value' in file '$input_file'."
	modify_input_parameters "$input_file"
}

# Main script logic.
if [[ $# -ne 0 ]]
then
	pretty_print "This is a script to quickly create a new input file for GYSELA simulations within this script's directory."
	echo "The target file can be specified via the environment variable INPUTFILEPATH."
	exit 1
fi

if ! define_input_path
then
	exit 1
fi

generate_input_file_copy
exit 0