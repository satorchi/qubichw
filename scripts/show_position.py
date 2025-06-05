#!/usr/bin/env python3
'''
$Id: show_position.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 05 Jun 2025 19:55:32 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

show the current position of the observation mount
'''
import time
import datetime as dt
from qubichk.obsmount import obsmount

mount = obsmount()
maxwait = 16
tstart = dt.datetime.now().timestamp()
ans = mount.show_azel()
while not ans:
    time.sleep(2)
    ans = mount.show_azel()
    now = dt.datetime.now().timestamp()
    delta = now - tstart
    if delta>maxwait: break

    
