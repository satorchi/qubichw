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
         tstart   : start time (default is now)
         tend     : end time (default is defined by duration)
         duration : duration in seconds.
             By default, this is a near endless loop and must be stopped manually with do_end_observation.py

EXAMPLE:

$ do_constant_elevation_scanning.py el=50 azmin=155 azmax=205 tstart=2026-03-26T10:40:34 tend=2026-03-26 12:40:49 title=Moon

'''
import sys
import datetime as dt
UTC = dt.timezone.utc
from satorchipy.utilities import parseargs
from satorchipy.datefunctions import utcnow
from pystudio import pystudio
from qubichk.obsmount import obsmount

parameterList = ['el',
                 'azmin',
                 'azmax',
                 'duration',
                 'tstart',
                 'tend',
                 'Voffset',
                 'Tbath',
                 'title',
                 'comment']
options = parseargs(sys.argv,expected_args=parameterList)
datefmt = '%Y-%m-%d %H:%M:%S'

def printmsg(msg):
    '''
    print the message on the screen
    '''
    print('[%s] - %s' % (utcnow().strftime(datefmt),msg))
    return

def cli():
    dispatcher = pystudio()
    ack = dispatcher.subscribe_dispatcher()

    mount = obsmount()
    
    #####################################
    # defaults    
    if options['title'] is None:
        dataset_name = 'constant_elevation_scan_%.1f' % el
    else:
        dataset_name = options['title']
    if options['comment'] is None:
        comment = 'constant elevation scanning sequence sent by pystudio'
    else:
        comment = options['comment']

    if options['el'] is None:
        el = 50
    else:
        el = options['el']
    if options['azmin'] is None:
        azmin = 135
    else:
        azmin = options['azmin']
    if options['azmax'] is None:
        azmax = 225
    else:
        azmax = options['azmax']

    if options['tstart'] is None:
        start_time = utcnow()
    else:
        # correct for ambiguous timezone
        start_time = tstart.replace(tzone=UTC)
        
    ## the rest of the defaults are defined in dispatcher.start_observation() and in obsmount.do_constant_elevation_scanning()

    ####### start immediately by going to the starting position ##########
    ack = mount.goto_el(el)
    if not ack['ok']:
        printmsg('Scan unable to send elevation command to observation mount')
        return
    
    azel = mount.wait_for_arrival(el=el)
    if not azel['ok']:
        printmsg('Did not successfully get to elevation position: %.3f degrees' % el)
        return
        
    ack = mount.goto_az(azmin)
    if not ack['ok']:
        printmsg('Scan unable to send azimuth command to observation mount')
        return
        
    azel = mount.wait_for_arrival(az=azmin)
    if not azel['ok']:
        printmsg('Scan did not successfully get to starting azimuth position: %.3f degrees' % azmin)
        return

    #### wait for start time if necessary ####
    now = utcnow()
    if now<start_time:
        wait_delta = start_time - now
        wait_before_start = wait_delta.total_seconds()
        printmsg('waiting until %s (%i seconds)' % (start_time.strftime(datefmt),wait_before_start))
        sleep(wait_before_start)
    
    #####################################
    # setup and start the acquisition
    dispatcher.start_observation(Voffset=options['Voffset'],Tbath=options['Tbath'],title=dataset_name,comment=comment)

    # run the scanning sequence from obsmount
    mount.do_constant_elevation_scanning(el=options['el'],azmin=options['azmin'],azmax=options['azmax'],
                                         tstart=options['tstart'],tend=options['tend'],duration=options['duration'])
    mount.disconnect()

    # stop the acquisition
    ack = dispatcher.end_observation()
    
    printmsg('Scan completed for %s' % dataset_name)
    ack = dispatcher.unsubscribe()
    return

if __name__ == '__main__':
    cli()
    

