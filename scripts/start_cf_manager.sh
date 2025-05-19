#!/bin/bash
# $Id: start_cf_manager.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Mon 19 May 2025 09:51:10 CEST
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
#
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
# script to start carbon fibre setup manager
# this is to be run on QUBIC PiGPS
# the following line should appear in crontab
# */5 * * * * /usr/local/bin/start_cf_manager.sh
#
if ! ps auxw | grep "f_commander.py" | grep -v -e grep -e SCREEN; then  
    echo "Carbon Fibre Manager not running";
    screen -X -S manager quit
    echo "Starting a new screen and launching the carbon fibre manager"
    screen -S manager -d -m /usr/local/bin/cf_commander.py manager	
else
    echo "Carbon Fibre Manager already running"
fi

#start_cf_manager.sh
