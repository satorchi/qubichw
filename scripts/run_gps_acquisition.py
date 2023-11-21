#!/usr/bin/env python3
'''
$Id: run_gps_acquisition.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 07 Sep 2023 08:09:50 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

run the acquisition for the SimpleRTK, ie. the calsource box position and orientation
'''
import sys
from qubichw.read_gps import acquire_gps

monitor = False
listener = None
verbosity = 0
for arg in sys.argv:
    if arg=='--monitor':
        monitor = True
        continue

    if arg.find('--verbosity=')==0:
        verbosity = eval(arg.split('=')[-1])
        continue

    if arg.find('--listener=')==0:
        listener = arg.split('=')[-1]
        continue
    
    

acquire_gps(listener=listener,monitor=monitor,verbosity=verbosity)
