#!/bin/bash
# I hate Bash. It's ugly. I miss Powershell.

pretty_print()
{
	printf "\n%s\n" "$1"
}

remove_all_input_file_copies()
{
	local input_files=()
	mapfile -d '' input_files < <(find . -maxdepth 1 -type f -name "data.*" -print0);
	local file_count=${#input_files[@]}

	if [[ $file_count -eq 0 ]]
	then
		pretty_print "No GYSELA input file copies found in the current directory. Skipping."
		return
	fi

	pretty_print "Found $file_count GYSELA input file copies in the current directory."
	pretty_print "Would you like them removed? (y/n)"
	read -r answer

	if [[ "$answer" != "y" ]]
	then
		pretty_print "Skipping input file copy removal."
		return
	fi

	for input_file in "${input_files[@]}"
	do
		echo "Removing input file copy: $input_file..."
		rm -f "$input_file"
	done

	pretty_print "All GYSELA input file copies removed. Success!"
}

remove_all_cmds()
{
	local cmds=()
	mapfile -d '' cmds < <(find . -maxdepth 1 -type f -name "go_*.cmd" -print0);
	local cmd_count=${#cmds[@]}

	if [[ $cmd_count -eq 0 ]]
	then
		pretty_print "No GYSELA command files found in the current directory. Skipping."
		return
	fi

	pretty_print "Found $cmd_count GYSELA command files in the current directory."
	pretty_print "Would you like them removed? (y/n)"
	read -r answer

	if [[ "$answer" != "y" ]]
	then
		pretty_print "Skipping command file removal."
		return
	fi

	for cmd_file in "${cmds[@]}"
	do
		echo "Removing command file: $cmd_file..."
		rm -f "$cmd_file"
	done

	pretty_print "All GYSELA command files removed. Hooray!"
}

remove_all_job_logs()
{
	local job_logs=()
	mapfile -d '' job_logs < <(find . -maxdepth 1 -type f -name "*.o*" -print0);
	local log_count=${#job_logs[@]}

	if [[ $log_count -eq 0 ]]
	then
		pretty_print "No PBS job log files found in the current directory. Skipping."
		return
	fi

	pretty_print "Found $log_count PBS job log files in the current directory."
	pretty_print "Would you like them removed? (y/n)"
	read -r answer

	if [[ "$answer" != "y" ]]
	then
		pretty_print "Skipping log removal."
		return
	fi

	for log_file in "${job_logs[@]}"
	do
		echo "Removing log file: $log_file..."
		rm -f "$log_file"
	done

	pretty_print "All job log files removed. Yay!"
}

remove_all_simulation_directories()
{
	pretty_print "Finding symbolic links for all simulation directories in the current folder..."
	local simulation_links=()
	mapfile -d '' simulation_links < <(find . -maxdepth 1 -type l -name 'DN_*' -print0)
	local link_count=${#simulation_links[@]}

	if [[ $link_count -eq 0 ]]
	then
		pretty_print "No simulation links found in the current folder. Aborting."
		return
	fi

	pretty_print "Found $link_count simulation links."
	pretty_print "Would you like to remove them and their associated directories? (y/n)"
	read -r answer

	if [[ "$answer" != "y" ]]
	then
		pretty_print "Skipping simulation directory removal."
		return
	fi

	for link in "${simulation_links[@]}"
	do
		local target_directory
		target_directory=$(readlink -f "$link")

		if [[ -d "$target_directory" ]]
		then
			echo "Removing directory: $target_directory..."
			rm -rf "$target_directory"
		fi

		echo "Removing symbolic link: $link..."
		rm "$link"
	done

	pretty_print "All simulation directories and their links have been removed. Yippee!"
}

# Main script logic.
pretty_print "This script removes all GYSELA simulation directories and associated output files."
pretty_print "Would you like to proceed? (y/n)"
read -r answer

if [[ "$answer" != "y" ]]
then
	pretty_print "Aborting cleanup. See ya!"
	exit 0
fi

remove_all_simulation_directories
remove_all_input_file_copies
remove_all_cmds
remove_all_job_logs
pretty_print "Cleanup complete!"