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
from qubichk.send_telegram import send_telegram, get_alarm_recipients, get_TelegramAddresses

known_users = get_TelegramAddresses()
alarm_recipients = get_alarm_recipients()

msg = "\nThis is QUBIC.  I hope you are well.  I'm fine."
msg += "\nI'm just testing the alarm system."
msg += "\n\nYou can now subscribe or unsubscribe yourself from the list of recipients for alarms"
msg += "\nby using the commands 'subscribe' and 'unsubscribe'.  You are currently subscribed."
msg += "\n\nI will check the compressor status every minute, and the UPS status every minute."
msg += "\nIf there's a problem, I'll send you a telegram every minute until the problem is resolved,"
msg += "\nor until you unsubscribe from the list."
msg += "\n\nBest regards from your friend,"
msg += "\nQUBIC"
for chatid in alarm_recipients:
    if chatid in known_users.keys():
        fullmsg = 'Hi %s!' % known_users[chatid]
    else:
        fullmsg = 'Hi!'
    fullmsg += '\n'+msg
    send_telegram(fullmsg,chatid=chatid)
    send_telegram(fullmsg,'Steve')

    
