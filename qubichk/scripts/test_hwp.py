#!/usr/bin/env python3
'''
$Id: test_hwp.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Fri 17 Jul 2026 07:51:10 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

test the HWP by cycling through the positions
'''
import sys,os
from time import sleep
from qubichk.hwp import get_hwp_info, send_hwp_command, hwp_wait_for_arrival
from qubichk.utilities import printmsg, assign_logfile
from satorchipy.utilities import parseargs


logfile = assign_logfile('hwp_test_log.txt')

parameterList = ['hwp_pos_min',
                 'hwp_pos_max',
                 'ncycles',
                 'max_fails']
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

if options['ncycles'] is None:
    ncycles = 4
else:
    ncycles = options['ncycles']

if options['max_fails'] is None:
    max_fails = 9
else:
    max_fails = options['max_fails']

def run_hwp_test(ncycles,hwp_pos_min,hwp_pos_max,max_fails):
    '''
    run the HWP test
    '''
    hwp_failure_counter = 0        
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

    npos = 1 + abs(hwp_pos_max - hwp_pos_min)
    npos_tot = npos*ncycles
    for loop_idx in range(npos_tot):
        
        hwp_pos += hwp_increment
        if hwp_pos>hwp_pos_max:
            hwp_increment *= -1
            hwp_pos = hwp_pos_max - 1
        if  hwp_pos<hwp_pos_min:
            hwp_increment *= -1
            hwp_pos = hwp_pos_min + 1
        printmsg('going to position %i' % hwp_pos, 'HWP',logfile=logfile)

        send_hwp_command('GOTO %i' % hwp_pos)
        hwpinfo = hwp_wait_for_arrival(hwp_pos)
        if not hwpinfo['ok']:
            hwp_failure_counter += 1
            errmsg = 'ERROR! %s.  Failure count: %i' % (hwpinfo['error_message'],hwp_failure_counter)
            printmsg(errmsg,'HWP',logfile=logfile)
            if hwp_failure_counter > max_fails:
                errmsg = 'ERROR! Maximum number of fails.  Giving up'
                printmsg(errmsg,'HWP',logfile=logfile)
                return False
    return True

if __name__=='__main__':
    run_hwp_test(ncycles,hwp_pos_min,hwp_pos_max,max_fails)

    

    
