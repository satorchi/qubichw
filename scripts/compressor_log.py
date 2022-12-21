#!/usr/bin/env python3
'''
$Id: compressor_log.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Tue 21 Dec 2021 23:10:40 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

log compressor status and send a Telegram if there's a problem
this script should be run from crontab every minute
'''
import os,sys,time
from qubichw.compressor import compressor
from qubichk.send_telegram import send_telegram, get_alarm_recipients

hk_dir = os.environ['HOME']+'/data/temperature/broadcast'

c = []
info = []
msg = []
status_msg = []
comm_error = False
online = True
ok = True
for compressor_num in [1,2]:
    logfile = '%s/compressor%i_log.txt' % (hk_dir,compressor_num)
    c.append(compressor(compressor_num))
    info.append(c[-1].status())

    h = open(logfile,'a')
    h.write(info[-1]['log_message']+'\n')
    h.close()

    status_msg.append(info[-1]['status_message'])
    msg.append(info[-1]['msg'])
    comm_error = comm_error or info[-1]['communication error']
    ok = ok and info[-1]['status']
    online = online and info[-1]['online']


if not ok:
    error_msg = '\n'.join(msg)
    alarm_recipients = get_alarm_recipients()

    if not comm_error:
        for chatid in alarm_recipients: send_telegram(error_msg,chatid=chatid)
    else:
        fullmsg = 'The following message is only sent to Steve'
        fullmsg += '\n- - - - - -\n'
        if online:
            fullmsg += error_msg
        else:
            fullmsg += '\n'.join(status_msg)
        send_telegram(fullmsg,'Steve')
