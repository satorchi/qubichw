#!/bin/bash
# $Id: clean-hk.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Sun 05 Jun 2022 17:14:29 CEST
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
#
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# clean the housekeeping directory and start again

HK_DIR=/home/qubic/data/temperature/broadcast
ARCHIVE_DIR=/archive

# find the start date of housekeeping data
HK_FILES=`ls $HK_DIR/*.txt|grep -v -e LABEL -e RAW -e VOLT -e botId`
START_TSTAMP=`for F in $HK_FILES;do head -1 $F;done|sort|head -1|gawk '{print $1}'`
START_DATE=`date --date="@$START_TSTAMP" +"%Y%m%d"`
if [ -z "$START_DATE" ];then
    START_DATE=`date --date="$START_TSTAMP" +"%Y%m%d"`
fi
ARCHIVE_HKDIR=$ARCHIVE_DIR/hk/data_$START_DATE

# stop the housekeeping server
killall -9 run_hkserver.py

# archive the data
archive-data.sh

# get the list of housekeeping files
cd $HK_DIR
HK_FILES="`/bin/ls -1 TEMP*.txt\
  AVS*.txt\
  HEATER*.txt\
  compressor?_log.txt\
  MHS?.txt\
  PRESSURE?.txt`"


# check that everything was copied
for F in $HK_FILES; do
    chk=`diff $HK_DIR/$F $ARCHIVE_HKDIR/$F 2> /dev/null`
    if [ -n "$chk" ];then
	echo "ERROR:  file not copied: $F"
	exit
    fi
done
      
# clean up the housekeeping directory
rm -f $HK_FILES

# restart the housekeeping server
start_hkserver.sh

# clean-hk.sh
