#!/bin/bash
# $Id: start_ups.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Thu 29 Feb 2024 17:03:59 CET
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
#
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# start the ups service
# this should be run once as root on qubic-central
# it's in rc.local to start at boot up
# but if the service is not running, this is also called from the cron daemon periodically
# if the service is running, this script does nothing and exits quietly
	  

chk="$(ps axw|grep usbhid-ups|grep -v grep)"
if [ -z "$chk" ]
then
    /usr/local/ups/bin/usbhid-ups -s cyberpower -x port=/dev/cyberpower-usb
    sleep 2
fi

chk="$(ps axw|grep upsd|grep -v grep)"
if [ -z "$chk" ]
then
    /usr/local/ups/sbin/upsd
fi

#start_ups.sh

