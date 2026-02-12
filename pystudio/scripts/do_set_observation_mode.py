#!/usr/bin/env python3
'''
$Id: do_set_observation_mode.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 12 Feb 2026 11:28:16 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

setup the frontend for an observation, but don't start the acquisition
Note:  use do_start_observation.py to setup and start an acquisition
       use do_start_acquisition.py to start an acquisition with the current setup
'''
import sys
from satorchipy.utilities import parseargs
from pystudio import pystudio

parameterList = ['Voffset',
                 'Tbath']
options = parseargs(sys.argv,expected_args=parameterList)

def cli():
    dispatcher = pystudio()
    ack = dispatcher.subscribe_dispatcher()
    ack = dispatcher.set_observation_mode(Voffset=options['Voffset'],Tbath=options['Tbath'])
    ack = dispatcher.unsubscribe()
    return

if __name__ == '__main__':
    cli()

