#!/bin/bash
# $Id: start_calsource_manager.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $auth: Manuel Gonzalez (this script adapted from Manu's script)
# $created: Mon 24 Jun 2019 07:27:08 CEST
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
# 
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# script to start calibration source setup manager
# this is to be run on QUBIC PiGPS
# the following line should appear in crontab
# */5 * * * * /usr/local/bin/start_bot.sh
#
if ! ps auxw | grep "/usr/local/bin/run_bot.py" | grep -v -e grep -e SCREEN; then  
    echo "bot not running";
    screen -X -S bot quit
    echo "Starting a new screen and launching the bot"
    cd $HOME/data/temperature
    screen -S bot -d -m /usr/local/bin/run_bot.py
else
    echo "bot already running"
fi

#start_bot.sh
