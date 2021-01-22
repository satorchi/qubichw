#!/usr/bin/env python3
'''
$Id: mailip.py
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

cmd='hostname'
proc=subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out,err=proc.communicate()
hostname=out.decode().strip()

txtmsg = 'QUBIC is running on battery!'

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
