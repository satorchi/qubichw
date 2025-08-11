#!/usr/bin/env python3
'''
$Id: do_IV_sequence.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 11 Aug 2025 10:57:56 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

do an I-V measurement

the script without arguments will use the default values

you can choose settings on the command line

For example:

do_IV_sequence.py Tbath=0.325

'''
import sys
from satorchipy.utilities import parseargs
from pystudio import pystudio

parameterList = ['Voffset',
                 'amplitude',
                 'undersampling',
                 'increment',
                 'Tbath',
                 'duration',
                 'comment']
options = parseargs(sys.argv,expected_args=parameterList)

dispatcher = pystudio()
ack = dispatcher.subscribe_dispatcher()
ack = dispatcher.do_IV_measurement(Voffset=options['Voffset'],
                                   amplitude=options['amplitude'],
                                   undersampling=options['undersampling'],
                                   increment=options['increment'],
                                   Tbath=options['Tbath'],
                                   duration=options['duration'],
                                   comment=options['comment']
                                   )
ack = dispatcher.unsubscribe()


