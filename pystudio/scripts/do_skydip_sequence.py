#!/usr/bin/env python3
'''
$Id: do_skydip_sequence.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 28 May 2025 11:23:01 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

do the sky dip sequence:  up and down elevation at different azimuth

the script without arguments will use the default values
you can change parameters on the command line:

For example:
do_skydip_sequence.py azstep=5 azmin=61 azmax=115

'''
import sys
from satorchipy.utilities import parseargs
from pystudio import pystudio

parameterList = ['azstep',
                 'azmin',
                 'azmax',
                 'elmin',
                 'elmax',
                 'Voffset',
                 'Tbath',
                 'comment']
options = parseargs(sys.argv,expected_args=parameterList)

def cli():
    dispatcher = pystudio()
    ack = dispatcher.subscribe_dispatcher()
    ack = dispatcher.do_skydip(azstep=options['azstep'],
                               azmin=options['azmin'],
                               azmax=options['azmax'],
                               elmin=options['elmin'],
                               elmax=options['elmax'],
                               Voffset=options['Voffset'],
                               Tbath=options['Tbath'],
                               comment=options['comment']
                               )

    ack = dispatcher.unsubscribe()
    return

if __name__ == '__main__':
    cli()
    
