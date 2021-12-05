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
'''
import sys,time

from qubichk.hk_verify import check_compressors
from qubichk.send_telegram import send_telegram, get_alarm_recipients

ans = check_compressors(verbosity=0)


# try one more time if there was a communication error
if ans['communication error']:
    time.sleep(0.5)
    ans = check_compressors(verbosity=0)

msg = ans['error_message'] + '\n***********\n' + ans['message']
alarm_recipients = get_alarm_recipients()
if not ans['ok'] and not ans['communication error']:
    for rx in alarm_recipients:
        send_telegram(msg,rx)
if ans['communication error']:
    msg = 'The following message is only sent to Steve\n- - - - - -\n'+msg
    send_telegram(msg,'Steve')
