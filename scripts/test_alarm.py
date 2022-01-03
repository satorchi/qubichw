#!/usr/bin/env python3
'''
$Id: test_alarm.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Sun 05 Dec 2021 19:28:38 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

test the Telegram alarm 
'''
from qubichk.send_telegram import send_telegram, get_alarm_recipients

alarm_recipients = get_alarm_recipients()

msg = "\nThis is QUBIC.  I hope you are well.  I'm fine."
msg += "\nI'm just testing the alarm system."
msg += "\nI will check the compressor status every minute, and the UPS status every minute."
msg += "\nIf there's a problem, I'll send you a telegram."
msg += "\n\nPlease tell Steve that you received this message from me."
msg += "\n\nBest regards from your friend,"
msg += "\nQUBIC"
for chatid in alarm_recipients:
    fullmsg = 'Hi %s!' % rx
    fullmsg += '\n'+msg
    send_telegram(fullmsg,chatid=chatid)
    send_telegram(fullmsg,'Steve')

    
