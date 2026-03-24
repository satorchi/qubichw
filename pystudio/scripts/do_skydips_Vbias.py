#!/usr/bin/env python3
'''
$Id: do_skydips_Vbias.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 18 Mar 2026 18:04:23 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

do the sky dip sequence at one azimuth, for multiple Vbias

arguments:

  ndips : number of up/down sequence for each Vbias (up and down is one sequence)

For example:
do_skydips_Vbias.py az=90 Tbath=0.320 ndips=2

'''
import sys
from time import sleep
from satorchipy.utilities import parseargs
from pystudio import pystudio
from qubichk.obsmount import obsmount

parameterList = ['az',
                 'elmin',
                 'elmax',
                 'Vmin',
                 'Vmax',
                 'Vstep',
                 'ndips',
                 'Tbath',
                 'title',
                 'comment']
options = parseargs(sys.argv,expected_args=parameterList)

def cli():
    if options['title'] is None:
        title_prefix = 'SkyDip_Vbias'
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
    

    if options['elmin'] is None:
        elmin = 30
    else:
        elmin = options['elmin']
    if options['elmax'] is None:
        elmax = 70
    else:
        elmax = options['elmax']

    if options['ndips'] is None:
        ndips = 2
    else:
        ndips = options['ndips']

        
    mount = obsmount()

    if options['az'] is not None:
        ack = mount.goto_az(options['az'])
        ack = mount.wait_for_arrival(az=options['az'])
        if not ack['ok']:
            print('ERROR! Did not get to starting azimuth. quitting')
            return
        
    
    ack = mount.goto_el(elmin)
    ack = mount.wait_for_arrival(el=elmin)
    if not ack['ok']:
        print('ERROR! Did not get to starting elevation.  quitting.')
        return
        
    dispatcher = pystudio()
    ack = dispatcher.subscribe_dispatcher()
    ack = dispatcher.park_frontend()
    sleep(10)
    
    Vbias = Vmax
    while Vbias>=Vmin:

        
        title = '%s__%04.2fV' % (title_prefix,Vbias)
        ack = dispatcher.start_observation(Voffset=Vbias,
                                           Tbath=options['Tbath'],
                                           comment=options['comment'],
                                           title=title
                                           )


        for idx in range(ndips):
            ack = mount.goto_el(elmax)
            ack = mount.wait_for_arrival(el=elmax)
            if not ack['ok']:
                print('ERROR! Did not get to elevation: %.1f degrees.  quitting.' % elmax)
                return

            ack = mount.goto_el(elmin)
            ack = mount.wait_for_arrival(el=elmin)
            if not ack['ok']:
                print('ERROR! Did not get to elevation: %.1f degrees.  quitting.' % elmin)
                return
            
        ack = dispatcher.end_observation()
        ack = dispatcher.park_frontend()
        sleep(2)
        Vbias -= Vstep

        
        
    ack = dispatcher.end_observation()
    ack = dispatcher.park_frontend()
    ack = dispatcher.unsubscribe()
    return

if __name__ == '__main__':
    cli()
