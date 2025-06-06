#!/usr/bin/env python3
'''
$Id: run_MCP9808_acquisition.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Tue 18 Feb 2025 20:08:39 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.
run the acquisition for the MCP9808 temperature sensors in the calibration box
'''
import sys
from qubichw.read_MCP9808_thermometer import MCP9808

listener = None
verbosity = 0
for arg in sys.argv:
    if arg.find('--verbosity=')==0:
        verbosity = eval(arg.split('=')[-1])
        continue

    if arg.find('--listener=')==0:
        listener = arg.split('=')[-1]
        continue

thermometers = MCP9808(verbosity=verbosity)
cli = thermometers.acquire_MCP9808_temperatures(listener=listener)
