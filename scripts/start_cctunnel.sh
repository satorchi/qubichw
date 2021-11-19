#!/bin/bash
# $Id: start_cctunnel.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Fri 19 Nov 2021 17:00:15 CET
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
#
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
# check if the remote forward ssh tunnel to CC-IN2P3 is running, and if not, then start it
	  
if ! ps auxw | grep "ssh cctunnel" | grep -v -e grep -e SCREEN; then  
    echo "CC tunnel not running";
    screen -X -S cctunnel quit
    echo "Starting a new screen and launching the CC ssh tunnel"
    screen -S cctunnel -d -m ssh cctunnel
else
    echo "cc ssh tunnel already running"
fi

#start_cctunnel.sh
