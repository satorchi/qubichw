#!/bin/bash
# $Id: start_apctunnel.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Fri 19 Nov 2021 16:53:15 CET
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# check if the remote forward ssh tunnel to APC is running, and if not, then start it
	  
if ! ps auxw | grep "ssh apctunnel" | grep -v -e grep -e SCREEN; then  
    echo "APC tunnel not running";
    screen -X -S apctunnel quit
    echo "Starting a new screen and launching the APC ssh tunnel"
    screen -S apctunnel -d -m ssh apctunnel
else
    echo "apc ssh tunnel already running"
fi

#start_apctunnel.sh
