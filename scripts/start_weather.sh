#!/bin/bash
# $Id: start_weather.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Wed 07 Dec 2022 13:18:35 CET
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
#
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# start the server to log the weather

if ! ps auxw | grep "/usr/local/bin/weather.py" | grep -v -e grep -e SCREEN; then  
    echo "weather logger not running";
    screen -X -S weather quit
    echo "Starting a new screen and launching the weather logger"
    cd $HOME/data/temperature/broadcast
    screen -S weather -d -m /usr/local/bin/weather.py --log --period=3
else
    echo "weather logger already running"
fi

#start_weather.sh
