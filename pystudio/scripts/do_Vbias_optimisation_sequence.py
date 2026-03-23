#!/usr/bin/env python3
'''
$Id: do_Vbias_optimisation_sequence.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 18 Mar 2026 14:26:49 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

step through Vbias values
we usually do this with the carbon fibre running
'''
import sys
from satorchipy.utilities import parseargs
from pystudio import pystudio

parameterList = ['Vmin',
                 'Vmax',
                 'Vstep',
                 'Tbath',
                 'title',
                 'duration',
                 'comment']
options = parseargs(sys.argv,expected_args=parameterList)

def cli():
    if options['title'] is None:
        title_prefix = 'Vbias_optimisation_sequence'
    else:
        title_prefix = options['title']


    if options['Vmin'] is None:
        Vmin = 1.0
    else:
        Vmin = options['Vmin']
    if options['Vmax'] is None:
        Vmax = 3.0
    else:
        Vmax = options['Vmax']
    if options['Vstep'] is None:
        Vstep = 0.1
    else:
        Vstep = options['Vstep']
    

    if options['Tbath'] is None:
        Tbath = 0.360
    else:
        Tbath = options['Tbath']

    if options['duration'] is None:
        duration = 300
    else:
        duration = options['duration']

        
    dispatcher = pystudio()
    ack = dispatcher.subscribe_dispatcher()
    Vbias = Vmax
    while Vbias>=Vmin:

        ack = dispatcher.park_frontend()
        time.sleep(10)
        
        title = '%s__%04.2fV' % (title_prefix,Vbias)
        ack = dispatcher.start_observation(Voffset=Vbias,
                                           Tbath=Tbath,
                                           comment=options['comment'],
                                           title=title
                                           )

        time.sleep(duration)
        ack = dispatcher.end_observation()

        Vbias -= Vstep

        
    ack = dispatcher.unsubscribe()
    return

if __name__ == '__main__':
    cli()
