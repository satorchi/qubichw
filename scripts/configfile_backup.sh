#!/bin/bash
# $Id: configfile_backup.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Tue 30 Nov 2021 13:58:06 CET
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
#
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# backup the configuration files on qubic-central

FILES="/etc/lilo.conf\
 /etc/resolv.conf\
 /etc/dhcpd.conf\
 /etc/rc.d/rc.local\
 /etc/hosts\
 /etc/udev/rules.d/*.rules\
 /usr/local/sbin/firewall.sh\
 /home/qubic/.local/share/qubic/*\
 /usr/local/ups/etc/*.conf\
 /home/qubic/qubic.crontab\
 /home/satorchi/satorchi.crontab"

# extract latest crontab
sudo su qubic -c "crontab -l > /home/qubic/qubic.crontab"
sudo su satorchi -c "crontab -l > /home/satorchi/satorchi.crontab"

ARCHIVE_DIR=/archive
tar -cvf ${ARCHIVE_DIR}/qc_etc.tar $FILES
gzip -9 -f ${ARCHIVE_DIR}/qc_etc.tar

#configfile_backup.sh
