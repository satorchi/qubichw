#!/bin/bash
# $Id: start_calsource_acq.sh
# $auth: Manuel Gonzalez <manuel.gonzalez@ib.edu.ar>
# $created: Tue 30 Apr 11:48:53 CEST 2019
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
# 
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# script to start calibration source modulation socket transmission
# this is to be run on QUBIC PiGPS
# the following line should appear in crontab
# */5 * * * * /usr/local/bin/start_calsource_acq.sh
#
if ! ps -aux | grep "/usr/bin/python3 /usr/local/bin/read_calsource.py" | grep -v -e grep -e SCREEN; then  
	echo "Calsource acquisition not running";
	screen -X -S calsource quit
	echo "Starting a new screen and launching the acquisition"
	screen -S calsource -d -m /usr/bin/python3 /usr/local/bin/read_calsource.py	
else
	echo "Acquisition already running"
fi

#start_calsource_acq.sh
