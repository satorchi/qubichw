#!/bin/bash
# $Id: start_motorcontroller.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Tue 09 Sep 2025 13:55:14 CEST
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
#
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# check of the motor controller is running, and if not, start it in a gnu screen

# this is to be run on motor raspberrypi (192.168.2.103)
# the following line should appear in crontab
# */5 * * * * /home/pi/start_motorcontroller.sh
#
if ! ps auxw | grep 'python.*server.py config_2motors.json' | grep -v -e grep -e SCREEN; then  
    echo "motor control server not running";
    screen -X -S montura quit
    echo "Starting a new screen and launching the motor server"
    cd $HOME/gitlab/deployment_qubic/control_montura/old/python_application
    screen -S montura -d -m python ./server.py config_2motors.json
else
    echo "motor server already running"
fi

#start_motorcontroller.sh
