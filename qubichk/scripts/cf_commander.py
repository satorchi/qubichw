#!/usr/bin/env python3
'''
$Id: cf_commander.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 12 May 2025 13:31:01 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

This is the Carbon Fibre commander.

It has two components:  
   "commander" is the command line interface
   "manager" is run on the Raspberry Pi which interfaces with the hardware

by default, this script will run as the "commander"
invoke with command line argument "manager" to run the "manager"
'''
import sys
from qubichw.cf_configuration_manager import cf_configuration_manager

verbosity = 0
role = None
for arg in sys.argv:
    if arg.lower() == 'manager':
        role = 'manager'
        continue

    if arg.lower() == 'commander':
        role = 'commander'
        continue

    if arg.find('--verbosity=')==0:
        verbosity = eval(arg.split('=')[-1])
        continue

def cli():
    cli = cf_configuration_manager(role=role, verbosity=verbosity)
    return

if __name__ == '__main__':
    cli()
    


    
