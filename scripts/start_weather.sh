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

if ! ps auxw | grep "/usr/local/bin/weather.py" | grep -v -e grep -e SCREEN -e inside_weather; then  
    echo "weather logger not running";
    screen -X -S weather quit
    echo "Starting a new screen and launching the weather logger"
    cd $HOME/data/temperature/broadcast
    screen -S weather -d -m /usr/local/bin/weather.py --log --period=60 --logfile=$HOME/data/temperature/broadcast/weather.txt
else
    echo "weather logger already running"
fi


if ! ps auxw | grep "/usr/local/bin/weather.py" | grep inside_weather | grep -v -e grep -e SCREEN; then  
    echo "weather logger not running";
    screen -X -S inside_weather quit
    echo "Starting a new screen and launching the indoor weather logger"
    cd $HOME/data/temperature/broadcast
    screen -S inside_weather -d -m /usr/local/bin/weather.py --log --period=3 --logfile=$HOME/data/temperature/broadcast/inside_weather.txt --server=192.168.88.13
else
    echo "inside weather logger already running"
fi



#start_weather.sh
