#!/bin/bash
# $Id: mount_qubicstudio.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Tue 10 Nov 2026 17:46:04 CET
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
#
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# check if the qubicstudio computer shared directory is
# mounted, and mount it if necessary
#
# this is to be run on qubic-central in crontab so that qubicstudio can be
# mounted at startup, or later, automatically, without worrying about
# which machine comes up first

# check if qubicstudio is already mounted
chk=`mount|grep '/qs'`
if [ -n "$chk" ]; then
    exit
fi

# check that qubicstudio is responding on the network
chk=`ping -c 1 qubicstudio`
if [ -z "$chk" ];then
    echo "qubicstudio computer is not responding"
    exit
fi

# try to mount qubicstudio
mount /qs

# mount_qubicstudio.sh
