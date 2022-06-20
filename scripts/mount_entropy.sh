#!/bin/bash
# $Id: mount_entropy.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Mon 20 Jun 2022 10:42:26 CEST
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
#
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# check if the entropy computer (Major Tom) shared directory is
# mounted, and mount it if necessary
#
# this is to be run on qubic-central in crontab so that entropy can be
# mounted at startup, or later, automatically, without worrying about
# which machine comes up first

# check if entropy is already mounted
chk=`mount|grep '/entropy'`
if [ -n "$chk" ]; then
    exit
fi

# check that entropy is responding on the network
chk=`ping -c 1 entropy`
if [ -z "$chk" ];then
    echo "entropy computer is not responding"
    exit
fi

# try to mount entropy
mount /entropy

# mount_entropy.sh
