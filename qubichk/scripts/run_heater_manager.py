#!/usr/bin/env python3
'''
$Id: run_heater_manager.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 12 Mar 2025 11:00:49 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

run the heater modes manager
'''
import sys
from qubichw.heater import heater

verbosity = 0
for arg in sys.argv:
    if arg.find('--verbosity=')==0:
        verbosity = eval(arg.split('=')[-1])
        print('assigning verbosity level: %i' % verbosity)
        continue

heater_manager = heater(verbosity=verbosity)
cli = heater_manager.operation_loop()

