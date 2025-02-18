#!/usr/bin/env python3
'''
$Id: run_MCP9808_broadcast.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Tue 18 Feb 2025 19:23:02 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

broadcast the MCP9808 temperature sensor data from the calibration box
'''
import sys
from qubichw.read_MCP9808_thermometer import broadcast_temperatures

verbosity = 0
for arg in sys.argv:
    if arg.find('--verbosity=')==0:
        verbosity = eval(arg.split('=')[-1])
        continue

broadcast_temperatures(verbosity=verbosity)
