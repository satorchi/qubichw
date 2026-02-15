#!/usr/bin/env python3
'''
$Id: do_constant_elevation_scanning.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Sun 15 Feb 2026 09:24:56 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

do back-and-forth azimuth scanning at a constant elevation

OPTIONS:
         el       : elevation position during scanning
         azmin    : azimuth start position
         azmax    : azimuth end position
         duration : duration in seconds.
             By default, this is a near endless loop and must be stopped manually with do_end_observation.py

EXAMPLE:

$ do_constant_elevation_scanning.py el=50 azmin=155 azmax=205 duration=10800 title=Moon
'''
import sys
from satorchipy.utilities import parseargs
from satorchipy.datefunctions import utcnow
from pystudio import pystudio
from qubichk.obsmount import obsmount

parameterList = ['el',
                 'azmin',
                 'azmax',
                 'Voffset',
                 'Tbath',
                 'title',
                 'comment']
options = parseargs(sys.argv,expected_args=parameterList)

def cli():
    dispatcher = pystudio()
    ack = dispatcher.subscribe_dispatcher()

    mount = obsmount()
    
    #####################################
    # defaults    
    if options['comment'] is None:
        comment = 'constant elevation scanning sequence sent by pystudio'
    else:
        comment = options['comment']
    if options['el'] is None:
        el = 50
    else:
        el = options['el']
    if options['title'] is None:
        dataset_name = 'constant_elevation_scan_%.1f' % el
    else:
        dataset_name = options['title']

    ## the rest of the defaults are defined in obsmount.do_constant_elevation_scanning()

    
    #####################################
    # setup and start the acquisition
    dispatcher.start_observation(Voffset=options['Voffset'],Tbath=options['Tbath'],title=dataset_name,comment=comment)

    # run the scanning sequence from obsmount
    mount.do_constant_elevation_scanning(el=el,azmin=options['azmin'],azmax=options['azmax'],duration=options['duration'])
    mount.disconnect()

    # stop the acquisition
    ack = dispatcher.end_observation()
    
    print('%s - Scan completed for %s' % (utcnow().strftime('%Y-%m-%d %H:%M:%S'),dataset_name))
    return

    ack = dispatcher.unsubscribe()
    return

if __name__ == '__main__':
    cli()
    

