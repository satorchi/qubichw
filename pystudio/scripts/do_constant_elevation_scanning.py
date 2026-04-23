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
from time import sleep
import datetime as dt
UTC = dt.timezone.utc
from satorchipy.utilities import parseargs
from satorchipy.datefunctions import utcnow
from pystudio import pystudio
from qubichk.obsmount import obsmount
from qubichk.hwp import get_hwp_info, send_hwp_command, hwp_wait_for_arrival

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


def do_constant_elevation_scanning(mount=None,el=None,azmin=None,azmax=None,tstart=None,tend=None,duration=None):
    '''
    do azimuth back and forth scanning at a given elevation

    ARGUMENTS:
        mount    : an obsmount() object
        el       : elevation position during scanning
        azmin    : azimuth start position
        azmax    : azimuth end position
        tstart   : datetime object for start time (default is now)
        tend     : datetime object for end time (default is defined by duration)
        duration : duration in seconds.
             By default, this is a near endless loop and must be stopped manually with ctrl-c and do_end_observation.py

    NOTE: 2026-04-23 18:10:39 this was moved from the obsmount() class in order to integrate the HWP movement
    '''
    if mount is None: mount = obsmount()
    if el is None: el = 50
    if azmin is None: azmin = 155
    if azmax is None: azmax = 205

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

    # move HWP to start position
    hwp_pos = 1
    hwp_increment = 1
    hwpinfo = get_hwp_info()
    is_arrived = hwpinfo['dir']=='STOPPED' and hwpinfo['pos']==str(hwp_pos)
    if not is_arrived:
        hwp_send_command('POS %i' % hwp_pos)
        hwpinfo = hwp_wait_for_arrival(hwp_pos)
    is_arrived = hwpinfo['dir']=='STOPPED' and hwpinfo['pos']==str(hwp_pos)

    # check if it's ok to use the HWP
    use_hwp = True
    if not is_arrived:
        print('ERROR! Problem with HWP: %s' % hwpinfo['error_message'])
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
                errmsg = 'Azimuth scan did not successfully get to azimuth position: %.3f degrees' % azlimit
                mount.printmsg(errmsg,threshold=0)
                mount.printmsg('Azimuth scan trying to send command again',threshold=0)
                ack = mount.goto_az(azlimit)
                azel = mount.wait_for_arrival(az=azlimit)

                if not azel['ok']:
                    errmsg += ' after two attempts to send command.  Trying a reset.'
                    mount.printmsg(errmsg)
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
                if hwp_pos>7 or hwp_pos<1:
                    hwp_increment -= hwp_increment
                    hwp_pos += 2*hwp_increment
                hwp_send_command('POS %i' % hwp_pos)
                hwpinfo = hwp_wait_for_arrival(hwp_pos,maxwait=15)
                if not hwpinfo['ok']:
                    print('ERROR with HWP: %s' % hwpinfo['error_message'])
                    use_hwp = False
                          
                
                

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
        dispatcher.printmsg('Scan unable to send elevation command to observation mount')
        return
    
    azel = mount.wait_for_arrival(el=el)
    if not azel['ok']:
        dispatcher.printmsg('Did not successfully get to elevation position: %.3f degrees' % el)
        return
        
    ack = mount.goto_az(azmin)
    if not ack['ok']:
        dispatcher.printmsg('Scan unable to send azimuth command to observation mount')
        return
        
    azel = mount.wait_for_arrival(az=azmin)
    if not azel['ok']:
        dispatcher.printmsg('Scan did not successfully get to starting azimuth position: %.3f degrees' % azmin)
        return

    #### wait for start time if necessary ####
    now = utcnow()
    if now<start_time:
        wait_delta = start_time - now
        wait_before_start = wait_delta.total_seconds()
        dispatcher.printmsg('waiting until %s (%i seconds)' % (start_time.strftime(datefmt),wait_before_start))
        sleep(wait_before_start)
    
    #####################################
    # setup and start the acquisition
    dispatcher.start_observation(Voffset=options['Voffset'],Tbath=options['Tbath'],title=dataset_name,comment=comment)

    # run the scanning sequence from obsmount
    do_constant_elevation_scanning(mount,el=options['el'],azmin=options['azmin'],azmax=options['azmax'],
                                  tstart=options['tstart'],tend=options['tend'],duration=options['duration'])

    # stop the acquisition
    ack = dispatcher.end_observation()
    
    dispatcher.printmsg('Scan completed for %s' % dataset_name)
    mount.disconnect()
    ack = dispatcher.unsubscribe()
    return

if __name__ == '__main__':
    cli()
    

