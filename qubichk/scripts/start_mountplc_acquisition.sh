#!/bin/bash
# $Id: start_mountrplc_acquisition.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Mon 01 Dec 2025 15:41:51 CET
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
#
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# script to start the fast acquisition of data from the mount PLC
# this is to be run on qubic-central
# the following line should appear in crontab
# */5 * * * * $HOME/.local/bin/start_mountplc_acquisition.sh
#
# argument: dump directory
dump_dir="$1"
if ! ps auxw | grep "$HOME/.local/bin/mountplc_acquisition.py" | grep -v -e grep -e SCREEN; then  
    echo "PLC acquistion not running";
    screen -X -S mountPLC quit
    echo "Starting a new screen and launching the PLC acquisition"
    cd $HOME/data/temperature
    screen -S mountPLC -d -m $HOME/.local/bin/mountplc_acquisition.py $dump_dir
else
    echo "mountplc acquisition is already running"
fi

#start_mountplc_acquisition.sh

	  
