#!/usr/bin/env python
'''
$Id: run_horn_monitor.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 25 Apr 2019 19:26:32 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

run the horn switch monitor
'''
from qubichk.horn_monitor import horn_monitor

mon = horn_monitor()
mon.listen_to_horns()
