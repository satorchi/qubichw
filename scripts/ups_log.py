#!/usr/bin/env python3
'''
$Id: ups_log.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 29 Nov 2021 17:36:29 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

output logging information from the UPS, save to the housekeeping directory
'''
from qubichk.ups import get_ups_info
from qubichk.send_telegram import send_telegram
from qubichk.hk_verify import alarm_recipients


hk_dir = '/home/qubic/data/temperature/broadcast'

h = open(hk_dir+'/ups_log.txt','a')
info = get_ups_info()
logline = info['log message']+'\n'
h.write(logline)
h.close()

if info['alarm']:
    for rx in alarm_recipients:
        send_telegram(info['full message'],rx)

