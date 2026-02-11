#!/usr/bin/env python3
'''
$Id: do_start_observation.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 05 Feb 2026 19:11:40 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

start an observation
the script without arguments will use the default values

you can choose settings on the command line

For example:

do_start_observation.py title=noise_measurement 
'''
import sys, time
from satorchipy.utilities import parseargs
from pystudio import pystudio

parameterList = ['Voffset',
                 'Tbath',
                 'duration',
                 'comment',
                 'title']
options = parseargs(sys.argv,expected_args=parameterList)

def cli():
    dispatcher = pystudio()
    ack = dispatcher.subscribe_dispatcher()
    ack = dispatcher.start_observation(Voffset=options['Voffset'],
                                       Tbath=options['Tbath'],
                                       comment=options['comment'],
                                       title=options['title']
                                       )

    if options['duration'] is not None:
        time.sleep(options['duration'])
        ack = dispatcher.end_observation()
        ack = dispatcher.unsubscribe()
        return
    
    return

if __name__ == '__main__':
    cli()


