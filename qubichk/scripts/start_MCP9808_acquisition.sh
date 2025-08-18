#!/bin/bash
# $Id: start_MCP9808_acquisition.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Tue 18 Feb 2025 19:52:58 CET
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
#
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
# start the SimpleRTK data acquisition in a screen

if ! ps -aux | grep "run_MCP9808_acquisition.py" | grep -v -e grep -e SCREEN; then  
	echo "MCP9808 acquisition not running";
	screen -X -S MCP9808 quit
	echo "Starting a new screen and launching the acquisition"
	screen -S MCP9808 -d -m run_MCP9808_acquisition.py	
else
	echo "Acquisition already running"
fi

#start_MCP9808_acquisition.sh
