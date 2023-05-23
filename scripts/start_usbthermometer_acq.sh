#!/bin/bash
'''
$Id: start_usbthermometer_acq.sh
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Tue 23 May 2023 07:34:02 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

start the usbthermometer reading and broadcasting
'''
if ! ps -aux | grep "read_usbthermometer.py" | grep -v -e grep -e SCREEN; then  
	echo "Usbthermometer acquisition not running";
	screen -X -S usbthermometer quit
	echo "Starting a new screen and launching the acquisition"
	screen -S usbthermometer -d -m /usr/local/bin/read_usbthermometer.py	
else
	echo "Acquisition already running"
fi

#start_usbthermometer_acq.sh
