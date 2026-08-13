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
import sys,re
from qubichw.cf_configuration_manager import cf_configuration_manager, valid_commands

verbosity = 1
role = None
cmd_list = []
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

    # check if we just want to send commands and not enter the loop
    if arg.lower()=='status':
        role = 'bot'
        cmd_list.append('status')
        continue
    
    for dev in valid_commands.keys():
        pattern = '.*%s...:' % dev
        match = re.search(pattern,arg)
        if match:
            role = 'bot'
            cmd_list.append(arg)
            

def cli():
    cf = cf_configuration_manager(role=role, verbosity=verbosity)
    if len(cmd_list)==0: return
    cmds = ' '.join(cmd_list)
    cf.send_command(cmds)
    ans = cf.listen_for_acknowledgement()
    return

if __name__ == '__main__':
    cli()
