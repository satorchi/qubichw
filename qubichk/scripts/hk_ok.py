#!/usr/bin/env python3
'''
$Id: hk_ok.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 12 Oct 2020 09:37:44 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

check if QUBIC housekeeping is running
'''
import sys

from qubichk.hk_verify import hk_ok
from qubichk.send_telegram import send_telegram

if __name__=='__main__':
    verbosity = 1
    for arg in sys.argv:
        if arg=='--silent':
            verbosity = 0
            continue
        
    ret = hk_ok(verbosity=verbosity)

    if verbosity>0: send_telegram(ret['full_message'])

    
