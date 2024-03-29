#!/usr/bin/env python3
'''
$Id: run_gps_broadcast.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 07 Sep 2023 08:26:08 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

run the broadcasting of the SimpleRTK data.  i.e. the calsource box position and orientation
'''
import sys
from qubichw.read_gps import broadcast_gps

verbosity = 0
for arg in sys.argv:
    if arg.find('--verbosity=')==0:
        verbosity = eval(arg.split('=')[-1])
        continue

broadcast_gps(verbosity=verbosity)
