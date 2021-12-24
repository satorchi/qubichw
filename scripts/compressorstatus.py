#!/usr/bin/env python3
'''
$Id: compressorstatus.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 24 Nov 2021 16:41:10 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.
check compressor status, and send a Telegram message if not okay
run this from crontab at regular intervals

Fri 24 Dec 2021 16:46:12 CET: This script is DEPRECATED.  Use compressor_log.py instead. 
'''
import sys,time

from qubichk.hk_verify import check_compressors
from qubichk.send_telegram import send_telegram, get_alarm_recipients

try_counter = 0
ans = check_compressors(verbosity=0)

# try a few times in case of communication error
while ans['communication error'] and try_counter<4:
    time.sleep(0.5)
    ans = check_compressors(verbosity=0)
    try_counter += 1
ans['communication attempts'] = try_counter+1
 
msg = ans['error_message'] + '\n***********\n' + ans['message']
alarm_recipients = get_alarm_recipients()
if not ans['ok'] and not ans['communication error']:
    for rx in alarm_recipients:
        send_telegram(msg,rx)

if ans['communication error']:
    fullmsg = 'The following message is only sent to Steve'
    fullmsg += '\ncommunication attempts: %i' % try_counter
    fullmsg += '\n- - - - - -\n' + msg
    send_telegram(fullmsg,'Steve')
