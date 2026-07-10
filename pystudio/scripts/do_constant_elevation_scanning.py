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
         el         : elevation position during scanning
         azmin      : azimuth start position
         azmax      : azimuth end position
         tstart     : start time (default is now)
         tend       : end time (default is defined by duration)
         duration   : duration in seconds.
             By default, this is a near endless loop and must be stopped manually with do_end_observation.py
         use_hwp    : cycle the HWP position after every there-and-back scan (default: no)
         velocity   : azimuth velocity (default: 1 degree/sec)
         hwp_settle : settling time after HWP repositioning before continuing the scan (default: 0)

EXAMPLE:

$ do_constant_elevation_scanning.py el=50 azmin=155 azmax=205 tstart=2026-03-26T10:40:34 tend=2026-03-26 12:40:49 title=Moon

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

parameterList = ['el',
                 'azmin',
                 'azmax',
                 'duration',
                 'tstart',
                 'tend',
                 'Voffset',
                 'Tbath',
                 'title',
                 'comment',
                 'use_hwp',
                 'hwp_settle',
                 'velocity',
                 'hwp_pos_min',
                 'hwp_pos_max']
options = parseargs(sys.argv,expected_args=parameterList)
datefmt = '%Y-%m-%d %H:%M:%S'

if options['hwp_pos_min'] is None:
    hwp_pos_min = 2
else:
    hwp_pos_min = options['hwp_pos_min']

if options['hwp_pos_max'] is None:
    hwp_pos_max = 6
else:
    hwp_pos_max = options['hwp_pos_max']
    
Tbath_precision = 0.0005
def do_constant_elevation_scanning(mount=None, dispatcher=None,
                                   el=None,azmin=None,azmax=None,
                                   tstart=None,tend=None,duration=None,
                                   use_hwp=None,velocity=None,hwp_settle=None):
    '''
    do azimuth back and forth scanning at a given elevation

    ARGUMENTS:
        mount      : an obsmount() object
        dispatcher : a pystudio() object
        el         : elevation position during scanning
        azmin      : azimuth start position
        azmax      : azimuth end position
        tstart     : datetime object for start time (default is now)
        tend       : datetime object for end time (default is defined by duration)
        duration   : duration in seconds.
             By default, this is a near endless loop and must be stopped manually with ctrl-c and do_end_observation.py
        use_hwp    : cycle the HWP position after every there-and-back scan (default: True)
        velocity   : scanning velocity (default is 1 degree per second)
        hwp_settle : settling time after HWP repositioning before continuing the scan (default: 0)
    
    NOTE: 2026-04-23 18:10:39 this module was moved from the obsmount() class in order to integrate the HWP movement
    '''
    if mount is None: mount = obsmount()
    if dispatcher is None: dispatcher = pystudio()        
    if el is None: el = 50
    if azmin is None: azmin = 155
    if azmax is None: azmax = 205
    if use_hwp is None: use_hwp = True

    if tstart is None:
        start_time = utcnow()
    else:
        # correct for ambiguous timezone
        start_time = tstart.replace(tzinfo=UTC)

    if duration is None:
        duration_delta = timedelta(days=30) # must end observation manually
    else:
        duration_delta = timedelta(seconds=duration)

    if tend is None:
        end_time = start_time + duration_delta
    else:
        end_time = tend.replace(tzinfo=UTC)

    if velocity is None:
        velocity = 1
    mount.set_az_speed(velocity)

    if use_hwp:
        hwp_failure_counter = 0

        # we will switch off the bath temperature PID before each HWP movement: 2026-05-20 17:39:37
        # not a good idea: 2026-05-20 19:20:20
        # see data: 2026-05-20_16.43.49__test_scan_temperature_control_off_during_hwp_movement
        mgc = iMACRT(device='mgc')

        # hack to flush wrong response
        for ctr in range(10):
            pidstate = mgc.get_mgc_pid()
        printmsg('PID state: %s' % pidstate,'iMACRT-MGC',logfile=logfile)
        
        hwp_increment = 1 # start by going in the positive direction

        # get or move to HWP start position
        hwpinfo = get_hwp_info()
        hwp_pos = hwpinfo['pos']
        if not hwpinfo['ok'] or hwp_pos==0:
            printmsg('moving to start position %i' % hwp_pos_min, 'HWP',logfile=logfile)
            send_hwp_command('GOTO %i' % hwp_pos_min)
            hwpinfo = hwp_wait_for_arrival(hwp_pos_min)
            hwp_pos = hwp_pos_min

        # check again
        is_arrived = hwpinfo['dir']=='STOPPED' and hwpinfo['pos']==hwp_pos
        if not is_arrived:
            hwp_failure_counter += 1
            send_hwp_command('GOTO %i' % hwp_pos)
            hwpinfo = hwp_wait_for_arrival(hwp_pos)

        # check if it's ok to use the HWP
        if not hwpinfo['ok']:
            hwp_failure_counter += 1
            errmsg = 'ERROR! %s.  Failure count: %i' % (hwpinfo['error_message'],hwp_failure_counter)
            printmsg(errmsg,'HWP',logfile=logfile)
            use_hwp = False
        
    now = utcnow()
    while now<end_time:
            
        for azlimit in [azmax, azmin]:
            ack = mount.goto_az(azlimit)

            # if axis still moving, wait a bit and try again
            if not ack['ok'] and ack['error'].find('already moving')>=0:
                sleep(5)
                ack = mount.goto_az(azlimit)

            # if still not ok, try to reset
            if not ack['ok']:
                ack = mount.reset()
                sleep(1)
                ack = mount.goto_az(azlimit)
                    
            sleep(1) # wait before next command
            azel = mount.wait_for_arrival(az=azlimit)
            if not azel['ok']:
                errmsg = 'Azimuth scan did not successfully get to azimuth position: %.3f degrees\n%s' % (azlimit,azel['error'])
                printmsg(errmsg,'obsmount',logfile=logfile)
                printmsg('Azimuth scan trying to send command again','obsmount',logfile=logfile)
                ack = mount.goto_az(azlimit)
                azel = mount.wait_for_arrival(az=azlimit)

                if not azel['ok']:
                    errmsg += ' after two attempts to send command.  Trying a reset.'
                    printmsg(errmsg,'obsmount',logfile=logfile)
                    ack = mount.reset()
                    sleep(0.5)
                    ack = mount.goto_az(azlimit)
                    azel = mount.wait_for_arrival(az=azlimit)

                    if not azel['ok']:
                        errmsg += ' Reset unsuccessful.  Aborting.'
                        azel['error'] = errmsg
                        return mount.return_with_error(azel)

        # go to next HWP position
        if use_hwp:
            hwp_pos += hwp_increment
            if hwp_pos>hwp_pos_max:
                hwp_increment *= -1
                hwp_pos = hwp_pos_max - 1
            if  hwp_pos<hwp_pos_min:
                hwp_increment *= -1
                hwp_pos = hwp_pos_min + 1
            printmsg('going to position %i' % hwp_pos, 'HWP',logfile=logfile)

            # switch off the temperature regulation before HWP movement
            # if pidstate==1: mgc.set_mgc_pid(0)

            # get the current bath temperature
            Tbath = mgc.get_mgc_measurement()
            
            send_hwp_command('GOTO %i' % hwp_pos)
            hwpinfo = hwp_wait_for_arrival(hwp_pos)
            if not hwpinfo['ok']:
                hwp_failure_counter += 1
                errmsg = 'ERROR! %s.  Failure count: %i' % (hwpinfo['error_message'],hwp_failure_counter)
                printmsg(errmsg,'HWP',logfile=logfile)
                if hwp_failure_counter > 9:
                    use_hwp = False
            else:
                if (Tbath is not None) and (pidstate==1):
                    printmsg('resetting bath temperature to %.1f mK to precision %.1f mK' % (Tbath*1000,Tbath_precision*1000),'iMACRT',logfile=logfile)
                    dispatcher.set_bath_temperature(Tbath,precision=Tbath_precision)
                if hwp_settle is not None and hwp_settle>0:
                    printmsg('waiting an extra %.1f seconds to resettle after HWP movement' % hwp_settle,'SCAN',logfile=logfile)
                    sleep(hwp_settle)
                
            # switch back on the temperature regulation
            # if pidstate==1: mgc.set_mgc_pid(1) # not a good strategy. 2026-05-20_16.43.49__test_scan_temperature_control_off_during_hwp_movement
            
        # check the time
        now = utcnow()            
    return True


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
        start_time = options['tstart'].replace(tzinfo=UTC)
        
    ## the rest of the defaults are defined in dispatcher.start_observation() and in obsmount.do_constant_elevation_scanning()

    ####### start immediately by going to the starting position ##########
    ack = mount.goto_el(el)
    if not ack['ok']:
        printmsg('Scan unable to send elevation command to observation mount','SCAN',logfile=logfile)
        return
    
    azel = mount.wait_for_arrival(el=el)
    if not azel['ok']:
        printmsg('Did not successfully get to elevation position: %.3f degrees' % el,'SCAN',logfile=logfile)
        return
        
    ack = mount.goto_az(azmin)
    if not ack['ok']:
        printmsg('Scan unable to send azimuth command to observation mount','SCAN',logfile=logfile)
        return
        
    azel = mount.wait_for_arrival(az=azmin)
    if not azel['ok']:
        printmsg('Scan did not successfully get to starting azimuth position: %.3f degrees' % azmin,'SCAN',logfile=logfile)
        return

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

    # run the scanning sequence from obsmount
    do_constant_elevation_scanning(mount=mount,dispatcher=dispatcher,
                                   el=options['el'],azmin=options['azmin'],azmax=options['azmax'],
                                   tstart=options['tstart'],tend=options['tend'],duration=options['duration'],
                                   use_hwp=options['use_hwp'],velocity=options['velocity'],hwp_settle=options['hwp_settle'])

    # stop the acquisition
    ack = dispatcher.end_observation()
    
    printmsg('Scan completed for %s' % dataset_name,'SCAN',logfile=logfile)
    mount.disconnect()
    ack = dispatcher.unsubscribe()
    return

if __name__ == '__main__':
    cli()
    

