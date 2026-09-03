'''
$Id: utilities.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 03 Sep 2026 14:35:15 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

utilities for observing scripts
'''
from time import sleep
from satorchipy.datefunctions import utcnow
from qubichk.utilities import printmsg, assign_logfile
datefmt = '%Y-%m-%d %H:%M:%S'
logfile = assign_logfile('pystudio_log.txt')

def wait_for_start_time(start_time):
    '''
    wait until the given time before continuing
    '''
    now = utcnow()
    if now>=start_time: return
    
    wait_delta = start_time - now
    wait_before_start = wait_delta.total_seconds()
    printmsg('waiting until %s (%i seconds)' % (start_time.strftime(datefmt),wait_before_start),'SCAN',logfile=logfile)
    sleep(wait_before_start)

    return
