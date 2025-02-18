#!/bin/bash
# $Id: start_MCP9808_broadcast.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Tue 18 Feb 2025 19:55:16 CET
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
#
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
# start the MCP9808 data broadcasting in a screen on calsource

if ! ps -aux | grep "run_MCP9808_broadcast.py" | grep -v -e grep -e SCREEN; then  
	echo "MCP9808 broadcasting is not running";
	screen -X -S MCP9808 quit
	echo "Starting a new screen and launching the broadcasting"
	screen -S MCP9808 -d -m python3 /usr/local/bin/run_MCP9808_broadcast.py	--verbosity=1
else
	echo "MCP9808 broadcasting is already running"
fi

#start_MCP9808_broadcast.sh
         
