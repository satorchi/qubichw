#!/usr/bin/env python3
'''
$Id: do_SQUID_sequence.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 11 Aug 2025 12:07:49 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

do a SQUID optimization measurement

the script without arguments will use the default parameters

You can choose parameters on the command line

For example:

do_NEP_sequence.py Voffset=5.5 amplitude=3
'''
from satorchipy.utilities import parseargs
from pystudio import pystudio

parameterList = ['Voffset',
                 'amplitude',
                 'undersampling',
                 'increment',
                 'duration',
                 'comment']
options = parseargs(sys.argv,parameterList=parameterList)

dispatcher = pystudio()
ack = dispatcher.subscribe_dispatcher()
ack = dispatcher.do_SQUID_measurement(Voffset=options['Voffset'],
                                    amplitude=options['amplitude'],
                                    undersampling=options['undersampling'],
                                    increment=options['increment'],
                                    duration=options['duration'],
                                    comment=options['comment']
                                    )

ack = dispatcher.unsubscribe()
