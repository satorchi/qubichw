#!/usr/bin/env python3
'''
$Id: do_park_frontend.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 11 Feb 2026 17:23:20 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

put the frontend into "parking" settings
sine bias with amplitude 1V and offset 8V
stop regulations
stop MGC3 temperature feedback loop
switch off calsources and carbon fibre
'''
from pystudio import pystudio
from qubichw.calsource_configuration_manager import calsource_configuration_manager
from qubichw.cf_configuration_manager import cf_configuration_manager

def cli():
    dispatcher = pystudio()
    dispatcher.verbosity = 1
    ack = dispatcher.subscribe_dispatcher()
    ack = dispatcher.park_frontend()
    ack = dispatcher.unsubscribe()

    calsrc = calsource_configuration_manager(role='bot', verbosity=1)
    ack = calsrc.send_command('calsource_150:off calsource_220:off modulator_ch1:output=off modulator_ch2:output=off')
    
    cf = cf_configuration_manager(role='bot', verbosity=1)
    ack = cf.send_command('cf:off')
    
    return

if __name__ == '__main__':
    cli()


