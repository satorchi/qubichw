#!/usr/bin/env python3
'''
$Id: ups_alarm.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Fri 22 Jan 15:17:12 CET 2021
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

send a warning that we're on UPS
'''

# following example at: http://docs.python.org/library/email-examples.html
import smtplib
from email.mime.text import MIMEText

import sys,os,time,subprocess

cmd = 'hostname'
proc = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out,err = proc.communicate()
hostname = out.decode().strip()

cmd = 'upsc cyberpower'
proc = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out,err = proc.communicate()

msg_list = []
lines = out.decode().split('\n')
for line in lines:
    col = line.split(':')
    if len(col)<2: continue
    
    parm = col[0].strip()
    val = col[1].strip()
    if parm=='battery.charge':
        msg_list.append('Battery level: %s' % val)
        continue

    if parm=='input.voltage':
        msg_list.append('Input voltage: %s' % val)
        continue

    

txtmsg = 'QUBIC is running on battery!\n%s' % '\n'.join(msg_list)

msg = MIMEText(txtmsg)
msg['Subject']='UPS alert from QUBIC'
msg['To']='Steve Torchinsky <satorchi@apc.in2p3.fr>'
msg['From']='%s <satorchi@apc.in2p3.fr>' % hostname
s = smtplib.SMTP('apcrelay.in2p3.fr')
s.sendmail(msg['From'], msg['To'], msg.as_string())
s.quit()

# send by Telegram
from qubichk.send_telegram import send_telegram
telegram = 'UPS alert from QUBIC\n\n%s' % (txtmsg)
send_telegram(telegram)
