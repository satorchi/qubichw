#!/usr/bin/env python3
'''
$Id: do_init_frontend.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Sat 16 Aug 2025 05:56:40 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

Initial configuration of the frontend to be done after power up and after flashing the FPGA
'''
import sys
from satorchipy.utilities import parseargs
from pystudio import pystudio

# note that PID, if provided, should be given as a triplet
parameterList = ['asicNum',
                 'nsamples',
                 'AcqMode',
                 'Apol',
                 'Spol',
                 'Vicm',
                 'Vocm',
                 'startRow',
                 'lastRow',
                 'column',
                 'CycleRawMode',
                 'RawMask',
                 'FeedbackRelay',
                 'Aplitude',
                 'offsetTable',
                 'feedbackTable',
                 'PID'
                 ]
options = parseargs(sys.argv,expected_args=parameterList)

def cli():
    dispatcher = pystudio()
    ack = dispatcher.subscribe_dispatcher()
    ack = dispatcher.init_frontend(asicNum=options['asicNum'],
                                   nsamples=options['nsamples'],
                                   AcqMode=options['AcqMode'],
                                   Apol=options['Apol'],
                                   Spol=options['Spol'],
                                   Vicm=options['Vicm'],
                                   Vocm=options['Vocm'],
                                   startRow=options['startRow'],
                                   lastRow=options['lastRow'],
                                   column=options['column'],
                                   CycleRawMode=options['CycleRawMode'],
                                   RawMask=options['RawMask'],
                                   FeedbackRelay=options['FeedbackRelay'],
                                   Aplitude=options['Aplitude'],
                                   offsetTable=options['offsetTable'],
                                   feedbackTable=options['feedbackTable'],
                                   PID=options['PID']
                                   )
    ack = dispatcher.unsubscribe()
    return

if __name__ == '__main__':
    cli()
    
