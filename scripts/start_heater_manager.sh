#!/bin/bash
# $Id: start_heater_manager.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Fri 14 Mar 2025 09:13:22 CET
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
#
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# start the heater manager to select heating modes

if ! ps -aux | grep "run_heater_manager.py" | grep -v -e grep -e SCREEN; then  
	echo "heater manager is not running";
	screen -X -S heater quit
	echo "Starting a new screen and launching the heater manager"
	screen -S heater -d -m python3 /usr/local/bin/run_heater_manager.py --verbosity=1
else
	echo "heater manager is already running"
fi
