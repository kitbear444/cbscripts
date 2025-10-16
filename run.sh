#!/bin/bash

# To make this script runnable, first grant it execute permissions:
# chmod +x run.sh
#
# Then, execute it from your terminal like this:
# ./run.sh your_file.cbscript
#
# To generate blocks.json, via command prompt at the minecraft server:
# java -DbundlerMainClass=net.minecraft.data.Main -jar {jar_path} --server --reports

echo "CBScript 1.20"

# Set the terminal title to the name of the file being processed
# Note: This might not work on all terminal emulators.
echo -ne "\033]0;$(basename "$1")\007"

# Change the current directory to the script's directory
cd "$(dirname "$0")"

# Run the python compiler script with the provided file
python3 compile.py "$1"

# Pause and wait for the user to press Enter
read -p "Press Enter to continue..."