#!/usr/bin/env python3
'''
$Id: mech_open.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 11 Nov 2026 16:08:17 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

open the Mechanical heat switch
'''
import sys

from qubichk.entropy_hk import entropy_hk
from qubichk.utilities import log_datefmt
from satorchipy.datefunctions import utcnow

hk = entropy_hk()
nsteps = 150000 # number of steps to open

# parse arguments
for arg in sys.argv:
    if arg.find('--nsteps=')>=0:
        val_str = arg.split('=')[-1].strip()
        nsteps = eval(val_str)
        continue        

now = utcnow()
print('%s | Opening Mechanical Heat Switch' % now.strftime(log_datefmt))
hk.mech_command(1,nsteps,'open')
    
