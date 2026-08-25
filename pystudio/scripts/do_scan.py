#!/usr/bin/env python3
'''
$Id: do_scan.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 24 Aug 2026 20:12:12 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

    do azimuth scanning

    ARGUMENTS:
        Voffset         : TES bias voltage
        Tbath           : desired TES bath temperature
        new_observation : reconfigure and restart FLL (default: False)
        el              : elevation for the scan
        azmin           : azimuth start position
        azmax           : azimuth end position
        tstart          : datetime object for start time (default is now)
        tend            : datetime object for end time (default is defined by duration)
        duration        : duration in seconds of the scan sequence
        velocity        : scanning velocity (default is 1 degree per second)
        use_hwp         : cycle the HWP position after every there-and-back scan (default: True)
        hwp_settle      : settling time after HWP repositioning before continuing the scan (default: 0)
        hwp_min_pos     : minimum position for HWP cycling (default: 1)
        hwp_max_pos     : maximum position for HWP cycling (default: 6)
'''
from satorchipy.utilities import parseargs
from pystudio import pystudio

parameterList = ['new_observation',
                 'el',
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

def cli():
    dispatcher = pystudio()
    ack = dispatcher.subscribe_dispatcher()

    dispatcher.do_scan(title=options['title'],Voffset=options['Voffset'],Tbath=options['Tbath'],
                       new_observation=options['new_observation'],
                       el=options['el'],azmin=options['azmin'],azmax=options['azmax'],
                       tstart=options['tstart'],tend=options['tend'],duration=options['duration'],
                       use_hwp=options['use_hwp'],hwp_pos_min=options['hwp_pos_min'],hwp_pos_max=options['hwp_pos_max'],
                       hwp_settle=options['hwp_settle'],
                       velocity=options['velocity']
                       )
    return

if __name__=='__main__':
    cli()
    
