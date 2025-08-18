#!/usr/bin/env python3
'''
$Id: plot_hornswitch.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Fri 26 Apr 2019 07:41:49 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

plot the latest horn switch inductance curves
'''
from glob import glob

from qubichk.horn_monitor import horn_monitor


m = horn_monitor()
files = m.recent_files()
m.plot_saved_event(files)

ans = input('Press <enter> to quit')
print('\n')
