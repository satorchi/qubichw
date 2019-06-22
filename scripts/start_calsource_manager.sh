#!/bin/bash
# $Id: start_calsource_manager.sh
# $auth: 
# $created: Tue 18 Jun 2019 11:53:45 CEST
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
# 
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# script to start calibration source setup manager
# this is to be run on QUBIC PiGPS
# the following line should appear in crontab
# */5 * * * * /usr/local/bin/start_calsource_manager.sh
#
if ! ps auxw | grep "/usr/bin/python /usr/local/bin/calsource_commander.py" | grep -v -e grep -e SCREEN; then  
	echo "Calsource Manager not running";
	screen -X -S manager quit
	echo "Starting a new screen and launching the calsource manager"
	screen -S manager -d -m /usr/bin/python /usr/local/bin/calsource_commander.py manager	
else
	echo "Calsource Manager already running"
fi

#start_calsource_manager.sh
