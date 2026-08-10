#!/usr/bin/env python3
'''
$Id: do_calsource_map.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 10 Aug 2026 11:29:58 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

do scanning to make a map of the calibration source
scan in azimuth, and then step in elevation

OPTIONS:
         elmin      : elevation start position
         elmax      : elevation end position
         azmin      : azimuth start position
         azmax      : azimuth end position
         tstart     : start time (default is now)
         velocity   : azimuth velocity (default: 1 degree/sec)
         title      : additional text to be added to title: calsource_map

EXAMPLE:

$ do_calsource_map.py elmin=30 elmax=70 azmin=-20 azmax=40 title="source_inside_dome"

'''

import sys
from time import sleep
import datetime as dt
UTC = dt.timezone.utc
from datetime import timedelta
from satorchipy.utilities import parseargs
from satorchipy.datefunctions import utcnow
from pystudio import pystudio
from qubichk.obsmount import obsmount
from qubichk.hwp import get_hwp_info, send_hwp_command, hwp_wait_for_arrival
from qubichk.utilities import printmsg, assign_logfile
from qubichk.imacrt import iMACRT
logfile = assign_logfile('pystudio_log.txt')

parameterList = ['elmin',
                 'elmax',
                 'elstep',
                 'azmin',
                 'azmax',
                 'tstart',
                 'Voffset',
                 'Tbath',
                 'title',
                 'comment',
                 'velocity',
                 'hwp_position'
                 ]
options = parseargs(sys.argv,expected_args=parameterList)
datefmt = '%Y-%m-%d %H:%M:%S'

    
Tbath_precision = 0.0005
def do_calsource_map(mount=None, dispatcher=None,
                     elmin=None,elmax=None,azmin=None,azmax=None,
                     tstart=None,
                     velocity=None,
                     hwp_position=None):
    '''
    do azimuth back and forth scan and then step elevation

    ARGUMENTS:
        mount        : an obsmount() object
        dispatcher   : a pystudio() object
        elmin        : elevation start position
        elmax        : elevation end position
        elstep       : elevation step size between azimuth scans
        azmin        : azimuth start position
        azmax        : azimuth end position
        tstart       : datetime object for start time (default is now)
        velocity     : scanning velocity (default is 1 degree per second)
        hwp_position :
    '''
    mount_failure_counter = 0
    max_fail = 100
    if mount is None: mount = obsmount()
    if dispatcher is None:
        dispatcher = pystudio()
        ack = dispatcher.subscribe_dispatcher()
    if elmin is None: elmin = 30
    if elmax is None: elmax = 70
    if azmin is None: azmin = -20
    if azmax is None: azmax = 40

    if tstart is None:
        start_time = utcnow()
    else:
        # correct for ambiguous timezone
        start_time = tstart.replace(tzinfo=UTC)

    if velocity is None:
        velocity = 1
    mount.set_az_speed(velocity)

    current_hwp_pos = None
    hwpinfo = get_hwp_info()
    if hwpinfo['ok']:
        current_hwp_pos = hwpinfo['pos']

    
    do_hwp_movement = False
    if current_hwp_pos is None or current_hwp_pos==0:
        do_hwp_movement = True
        if hwp_position is None:
            hwp_position = 4 # default
        if current_hwp_pos==hwp_position:
            do_hwp_movement = False
        
    
    if do_hwp_movement:
        hwp_failure_counter = 0
        
        # move HWP to desired position
        printmsg('moving to start position %i' % hwp_pos_min, 'HWP',logfile=logfile)
        send_hwp_command('GOTO %i' % hwp_position)
        hwpinfo = hwp_wait_for_arrival(hwp_position)

        # check again
        is_arrived = hwpinfo['dir']=='STOPPED' and hwpinfo['pos']==hwp_position
        if not is_arrived:
            hwp_failure_counter += 1
            send_hwp_command('GOTO %i' % hwp_position)
            hwpinfo = hwp_wait_for_arrival(hwp_position)

        # check if it's ok to use the HWP
        if not hwpinfo['ok']:
            hwp_failure_counter += 1
            errmsg = 'ERROR! %s.  Failure count: %i' % (hwpinfo['error_message'],hwp_failure_counter)
            printmsg(errmsg,'HWP',logfile=logfile)
        
    now = utcnow()
    el = elmin
    while el<=elmax:
        ack = mount.goto_el(el)
        # if axis still moving, wait a bit and try again
        if not ack['ok'] and ack['error'].find('already moving')>=0:
            mount_failure_counter += 1
            sleep(5)
            ack = mount.goto_el(el)

        # if still not ok, try to reset
        if not ack['ok']:
            mount_failure_counter += 1
            ack = mount.reset()
            sleep(1)
            ack = mount.goto_el(el)
            
        azel = mount.wait_for_arrival(el=el)
        if not azel['ok']:
            mount_failure_counter += 1
            errmsg = 'Mount did not successfully get to elevation position: %.3f degrees\n%s' % (el,azel['error'])
            printmsg(errmsg,'obsmount',logfile=logfile)
        
        for azlimit in [azmax, azmin]:
            ack = mount.goto_az(azlimit)

            # if axis still moving, wait a bit and try again
            if not ack['ok'] and ack['error'].find('already moving')>=0:
                mount_failure_counter += 1
                sleep(5)
                ack = mount.goto_az(azlimit)

            # if still not ok, try to reset
            if not ack['ok']:
                mount_failure_counter += 1
                ack = mount.reset()
                sleep(1)
                ack = mount.goto_az(azlimit)
                    
            sleep(1) # wait before next command
            azel = mount.wait_for_arrival(az=azlimit)
            if not azel['ok']:
                mount_failure_counter += 1
                errmsg = 'Azimuth scan did not successfully get to azimuth position: %.3f degrees\n%s' % (azlimit,azel['error'])
                printmsg(errmsg,'obsmount',logfile=logfile)
                printmsg('Azimuth scan trying to send command again','obsmount',logfile=logfile)
                ack = mount.goto_az(azlimit)
                azel = mount.wait_for_arrival(az=azlimit)

                if not azel['ok']:
                    mount_failure_counter += 1
                    errmsg += ' after two attempts to send command.  Trying a reset.'
                    printmsg(errmsg,'obsmount',logfile=logfile)
                    ack = mount.reset()
                    sleep(0.5)
                    ack = mount.goto_az(azlimit)
                    azel = mount.wait_for_arrival(az=azlimit)

                    if not azel['ok']:
                        mount_failure_counter += 1
                        errmsg += ' Reset unsuccessful.  Aborting.'
                        azel['error'] = errmsg
                        # check for maximum mount failures
                        if mount_failure_counter>max_fail: return mount.return_with_error(azel)
                        
        el += elstep
        now = utcnow()            
    return True


def cli():
    dispatcher = pystudio()
    ack = dispatcher.subscribe_dispatcher()

    mount = obsmount()
    fail_count = 0
    max_fail = 100
    
    #####################################
    # defaults    
    if options['title'] is None:
        dataset_name = 'calsource_map'
    else:
        dataset_name = 'calsource_map_%s' % options['title']
    if options['comment'] is None:
        comment = 'calsource map sequence sent by pystudio'
    else:
        comment = options['comment']

        
    ## the rest of the defaults are defined in the relevant modules


    #### wait for start time if necessary ####
    now = utcnow()
    if now<start_time:
        wait_delta = start_time - now
        wait_before_start = wait_delta.total_seconds()
        printmsg('waiting until %s (%i seconds)' % (start_time.strftime(datefmt),wait_before_start),'SCAN',logfile=logfile)
        sleep(wait_before_start)
    
    #####################################
    # setup and start the acquisition
    dispatcher.start_observation(Voffset=options['Voffset'],Tbath=options['Tbath'],title=dataset_name,comment=comment)

    # run the scanning sequence
    do_calsource_map(mount=mount,dispatcher=dispatcher,
                     elmin=options['elmin'],elmax=options['elmax'],elstep=options['elstep'],
                     azmin=options['azmin'],azmax=options['azmax'],
                     tstart=options['tstart'],
                     hwp_position=options['hwp_position'],
                     velocity=options['velocity'])

    # stop the acquisition
    ack = dispatcher.end_observation()
    
    printmsg('Scan completed for %s' % dataset_name,'SCAN',logfile=logfile)
    mount.disconnect()
    ack = dispatcher.unsubscribe()
    return

if __name__ == '__main__':
    cli()
    

