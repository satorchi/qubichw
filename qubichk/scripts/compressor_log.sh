#!/bin/bash
# $Id: compressor_log.sh
# $auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
# $created: Tue 30 Nov 2021 19:40:21 CET
# $license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt
#
#           This is free software: you are free to change and
#           redistribute it.  There is NO WARRANTY, to the extent
#           permitted by law.
#
# wrapper to log compressor status

HK_DIR=/home/qubic/data/temperature/broadcast
BIN_DIR=/home/qubic/.local/bin

${BIN_DIR}/compressor_commander.py 1 log >> ${HK_DIR}/compressor1_log.txt
${BIN_DIR}/compressor_commander.py 2 log >> ${HK_DIR}/compressor2_log.txt

#compressor_log.sh
