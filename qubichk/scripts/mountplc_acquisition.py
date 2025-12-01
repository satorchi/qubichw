#!/usr/bin/env python3
'''
$Id: mountplc_acquisition.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 01 Dec 2025 12:04:09 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

read mount position data from the PLC and dump it to binary data file
'''
from qubichk.obsmount import obsmount
from qubichk.utilities import make_errmsg

mount = obsmount()
keepgoing = True
while keepgoing:
    ans = mount.get_azel(dump=True)
    if not ans['ok']:
        errmsg = make_errmsg(ans['error'])
        print(errmsg)
        if errmsg.find('KeyboardInterrupt')>=0: 
            keepgoing = False
            
