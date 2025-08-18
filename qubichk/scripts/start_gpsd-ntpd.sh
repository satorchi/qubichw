#!/bin/bash
# $Id: start_gpsd-ntpd.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Mon 20 Jun 2022 11:32:17 CEST
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
#
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# start the GPS daemon if necessary
# start the ntp daemon if necessary
#
# this can be run from crontab on PiGPS to verify regularly that the daemons are running

# check if the gps device is present
GPS_DEV=`/bin/ls /dev/ttyAMA*|head -1`
if [ -z "$GPS_DEV" ]; then
    echo "no GPS device found!"
    exit
fi

# check of the gps daemon is running
# if not, start the gps daemon, and wait for it to connect
chk=`ps axw|grep gpsd|grep -v grep`
if [ -z "$chk" ]; then
    echo "starting gpsd"
    /usr/sbin/gpsd $GPS_DEV
    sleep 15
fi

# check if the ntp daemon is running
chk=`ps axw|grep ntpd|grep -v -e "start_gpsd" -e grep`
if [ -n "$chk" ]; then
    echo "ntpd is already running"
    echo $chk
    exit
fi

# if not, start the ntp daemon and allow for a big initial correction (flag: -g)
/usr/sbin/ntpd -q -g

/usr/sbin/ntpd
# start_gpsd-ntpd.sh

	  
