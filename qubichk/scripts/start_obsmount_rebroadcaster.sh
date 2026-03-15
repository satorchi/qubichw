#!/bin/bash
# $Id: start_obsmount_rebroadcaster.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Sun 15 Mar 2026 20:03:30 CET
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
#
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# start the observation mount rebroadcaster in a screen

if ! ps auxw | grep "/home/qubic/.local/bin/run_obsmount_rebroadcaster.py" | grep -v -e grep -e SCREEN; then  
    echo "Observation mount rebroadcaster server not running";
    screen -X -S obsmount_rebroadcaster quit
    echo "Starting a new screen and launching the observation mount rebroadcaster server"
    screen -S obsmount_rebroadcaster -d -m /home/qubic/.local/bin/run_obsmount_rebroadcaster.py
else
    echo "Observation mount rebroadcast server already running"
fi

# start_obsmount_rebroadcaster.sh
