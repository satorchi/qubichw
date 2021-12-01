#!/bin/bash
# $Id: archive-data.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Wed 15 Jul 2020 10:40:46 CEST
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# archive data for QUBIC.  This should be run by cron once a day

HK_DIR=/home/qubic/data/temperature/broadcast
FRIDGESCRIPTS_DIR=/home/qubic/data/temperature
#QS_DIR=pi@cam2:/qs2 # copy from the RaspberryPi because there's a problem with the Windows share on qubic-central
QS_DIR=/qs # 2021-11-30 11:52:06 back to samba mount on qubic-central
HWP_DIR=pi@hwp:/home/pi/HWP_QUBIC
ARCHIVE_DIR=/archive

CC_DIR=/sps/qubic/Data/Calib-TD
JUPYTER_DIR=/qubic/Data/Calib-TD

# find the start date of housekeeping data
HK_FILES=`ls $HK_DIR/*.txt|grep -v -e LABEL -e RAW -e VOLT -e botId`
START_TSTAMP=`for F in $HK_FILES;do head -1 $F;done|sort|head -1|gawk '{print $1}'`
START_DATE=`date --date="@$START_TSTAMP" +"%Y%m%d"`
ARCHIVE_HKDIR=$ARCHIVE_DIR/hk/data_$START_DATE

echo $ARCHIVE_HKDIR

# make a tar file of the qubic-central configuration
sudo /usr/local/bin/configfile_backup.sh

# make a tar file of the fridge cycling scripts
tar -cvf $ARCHIVE_DIR/fridgescripts.tar $FRIDGESCRIPTS_DIR/*.*
gzip -9 -f $ARCHIVE_DIR/fridgescripts.tar

# use rsync to copy to archive disk
rsync -avt $HK_DIR/ $ARCHIVE_HKDIR
rsync -avt $QS_DIR/QubicStudio $ARCHIVE_DIR
rsync -avt $QS_DIR/Script $ARCHIVE_DIR
rsync -avt $QS_DIR/Data/ $ARCHIVE_DIR
rsync -avt $HWP_DIR $ARCHIVE_DIR

# use rsync to copy to CC
rsync -avt $ARCHIVE_DIR/ cc:$CC_DIR

# use rsync to copy to apcjupyter
## Wed 15 Jul 2020 14:18:13 CEST apcjupyter has run out of space
## rsync -avt $ARCHIVE_DIR/ apcjupyter:$JUPYTER_DIR

