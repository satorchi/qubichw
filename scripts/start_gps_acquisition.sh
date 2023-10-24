#!/bin/bash
# $Id: start_gps_acquisition.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Tue 24 Oct 2023 07:46:03 CEST
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
#
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# start the SimpleRTK data acquisition in a screen

if ! ps -aux | grep "run_gps_acquisition.py" | grep -v -e grep -e SCREEN; then  
	echo "GPS acquisition not running";
	screen -X -S GPS quit
	echo "Starting a new screen and launching the acquisition"
	screen -S GPS -d -m /usr/local/bin/run_gps_acquisition.py	
else
	echo "Acquisition already running"
fi

#start_gps_acquisition.sh
