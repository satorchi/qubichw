#!/usr/bin/env python3
'''
$Id: do_DACoffset_measurement.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Tue 10 Feb 2026 08:25:28 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

do a short measurement which is used to calculate the DAC offset table
'''
import sys, time
from satorchipy.utilities import parseargs
from pystudio import pystudio

parameterList = ['Voffset',
                 'Tbath',
                 'duration',
                 'comment']
options = parseargs(sys.argv,expected_args=parameterList)

def cli():
    dispatcher = pystudio()
    ack = dispatcher.subscribe_dispatcher()
    ack = dispatcher.do_DACoffset_measurement(Voffset=options['Voffset'],
                                              Tbath=options['Tbath'],
                                              duration=options['duration'],
                                              comment=options['comment']
                                              )

    ack = dispatcher.unsubscribe()
    return

if __name__ == '__main__':
    cli()
