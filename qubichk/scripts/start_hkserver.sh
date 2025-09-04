#!/bin/bash
# $Id: start_hkserver.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $auth: Manuel Gonzalez (this script adapted from Manu's script)
# $created: Sat 22 Jun 2019 23:33:13 CEST
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
# 
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# script to start the hk broadcasting
# this is to be run on qubic-central
# the following line should appear in crontab
# */5 * * * * /home/qubic/.local/bin/start_hkserver.sh
#
if ! ps auxw | grep "/home/qubic/.local/bin/run_hkserver.py" | grep -v -e grep -e SCREEN; then  
    echo "HK server not running";
    screen -X -S hkserver quit
    echo "Starting a new screen and launching the HK server"
    cd $HOME/data/temperature/broadcast
    screen -S hkserver -d -m /home/qubic/.local/bin/run_hkserver.py
else
    echo "HK server already running"
fi

#start_hkserver.sh
