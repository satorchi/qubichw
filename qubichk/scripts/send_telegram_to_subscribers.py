#!/usr/bin/env python3
'''
$Id: send_telegram_to_subscribers.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 23 Jun 2025 10:59:10 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

send a telegram message to alarm subscribers
'''
import sys,os
from qubichk.send_telegram import send_telegram, get_alarm_recipients, get_TelegramAddresses

known_users = get_TelegramAddresses()
alarm_recipients = get_alarm_recipients()

msgfile = None
for idx,arg in enumerate(sys.argv):
    if idx==0: continue

    if os.path.isfile(arg):
        msgfile = arg
        continue

    if arg.find('=')>0:
        f = arg.split('=')[-1]
        if os.path.isfile(f):
            msgfilg = f
            continue


def cli():
    if msgfile is None:
        print('Please enter the name of a text file with your message')
        return None

    h = open(msgfile,'r')
    msg = h.read()
    h.close()


    for chatid in alarm_recipients:
        if chatid in known_users.keys():
            fullmsg = 'Hi %s!' % known_users[chatid]
        else:
            fullmsg = 'Hi!'
        fullmsg += '\n'+msg
        send_telegram(fullmsg,chatid=chatid)
    return

if __name__ == '__main__':
    cli()

    
