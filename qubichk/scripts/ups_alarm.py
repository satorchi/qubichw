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

from qubichk.ups import get_ups_info
from qubichk.send_telegram import send_telegram

info = get_ups_info()

# send by Telegram
send_telegram(info['full message'])
