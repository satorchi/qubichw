#!/usr/bin/env python3
'''
$Id: kill_all_fridge_cycles.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 09 Jun 2025 10:10:41 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

kill all the running fridge cycle scripts and stop all the heaters
'''
from qubichk.utilities import shellcommand
from qubichk.powersupply import PowerSupplies
import re

# kill the processes running fridge cycle scripts
out,err = shellcommand('ps axo pid,args')
pids_list = out.split('\n')
for pid_desc in pids_list:
    match = re.search('python.*cycle_.*fridge.*py',pid_desc)
    if not match: continue

    pid = pid_desc.split()[0]
    print('killing process:  %s' % pid_desc)
    cmd = 'kill -9 %s' % pid
    out,err = shellcommand(cmd)

    if len(err)>0: print(err)

# switch off the output to all heaters
print('switching off the output on all power supplies')
allsupplies = PowerSupplies()
allsupplies.off()


        

