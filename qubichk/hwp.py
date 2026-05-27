#!/usr/bin/env python3
'''
$Id: hwp.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 21 Jul 2022 13:54:08 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

Half Wave Plate methods for housekeeping acquisition
HWP control software by Carlos Reyes
'''
import os,socket,re
from time import sleep
from qubichk.utilities import ping,shellcommand,get_myip,get_known_hosts, printmsg, assign_logfile
from satorchipy.datefunctions import utcnow

known_hosts = get_known_hosts()
QC_IP = known_hosts['qubic-central']
HWP_IP = known_hosts['hwp']
MY_IP = get_myip()
LISTEN_PORT = 5455
CMD_PORT = 5454

cmd_help = {
    'HALT'         : 'stop HWP',
    'ENGA'         : 'engage hwp software to a well known position',
    'CAL'          : 'same as ENGA',
    'DEBUG'        : 'run custom routine helper',
    'GOTO'         : 'go to position (valid positions: 1 to 7)',
    'STEP'         : 'step motor (valid steps: 1 to 500)',
    'VEL'          : 'set Ton and Toff times as VELOCITY for the square wave signal for the motor driver',
    'DIS'          : 'disable motor',
    'EN'           : 'enable motor',
    'DIR'          : 'sets motor spin direction. Where <dir> is 0 (1-->7) and 1 (7-->1)'
}

logfile = assign_logfile('pystudio_log.txt')

def check_hwp_status():
    '''
    check the status of the HWP controller
    '''
    retval = {}
    retval['ok'] = True
    retval['error_message'] = 'NO ERROR MESSAGE'
    
    # check if hwp is responding
    ping_result = ping(HWP_IP,verbosity=0)
    if not ping_result['ok']:
        retval['ok'] = False
        retval['message'] = 'HWP is not responding on the network'
        retval['error_message'] = retval['message']
        retval['brief message'] = 'HWP unavailable'
        return retval

    # check if HWP server is running
    cmd = 'ssh hwp ps axwu'
    out,err = shellcommand(cmd)
    daemon = 'hwpctl.py'
    find_str = 'python.*%s' % daemon
    match = re.search(find_str,out)
    if match is None:
        retval['ok'] = False
        retval['message'] = 'HWP server not running'
        retval['error_message'] = '%s not running on HWP' % daemon
        retval['brief message'] = '%s not running' % daemon
        return retval
    
    return retval

def get_hwp_data():
    '''
    open a socket and get the HWP data from the controller
    '''
    retval = {}
    retval['ok'] = True
    retval['error_message'] = 'NO ERROR MESSAGE'
    retval['data message'] = None
    
    msg_rcv = None
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1)
    try:
        s.bind((MY_IP, LISTEN_PORT))
    except:
        s.close()
        retval['ok'] = False
        retval['error_message'] = 'HWP info unavailable: socket in use.'
        retval['message'] = 'HWP info unavailable: socket in use.  Try again.'
        retval['brief message'] = retval['message']
        return retval

    try:
        msg_rcv, addr = s.recvfrom(1024)
    except:
        s.close()
        retval['ok'] = False
        retval['message'] = 'HWP did not send info'
        retval['error_message'] = retval['message']
        retval['brief message'] = retval['message']
        return retval
    
    s.close()
    msg = msg_rcv.decode()
    retval['data message'] = msg
    return retval

def get_hwp_info():
    '''
    get the current position and direction of the HWP
    '''
    n_attempts = 4
    for idx in range(n_attempts):
        retval = get_hwp_data()
        if retval['ok']: break
        printmsg('ERROR! Attempt No. %i: %s' % (idx+1,retval['error_message']), 'HWP',logfile=logfile)
        sleep(0.4) 

    retval['pos'] = None
    retval['dir'] = None
    retval['motor'] = None
    if not retval['ok']:
        printmsg('ERROR! Could not get HWP info after %i attempts.' % n_attempts, 'HWP',logfile=logfile)
        return retval
        
    
    msg = retval['data message']
    if msg.find('motor not running')>0:
        motor_str = 'motor not running'
        pos_str = msg.split('motor')[0].split()[1]
        dir_str = 'STOPPED'
    else:        
        pos_str = msg.split('direction')[0].split()[1]
        dir_str = msg.split('direction:')[1].split(',')[0].strip()
        motor_str = msg.split(',')[-1].strip()

    try:
        pos = eval(pos_str)
    except:
        pos = pos_str

    retval['pos'] = pos
    retval['dir'] = dir_str
    retval['motor'] = motor_str       

    msg = 'HWP POS=%s, direction=%s, motor state=%s' % (pos_str,dir_str,motor_str)
    retval['brief message'] = msg
    retval['message'] = msg
    return retval


def show_hwp_help():
    '''
    print a help text
    '''
    for cmd in cmd_help.keys():
        print('%s: %s' % (cmd.ljust(8),cmd_help[cmd]))
    return

def send_hwp_command(cmd):
    '''
    send a command to the HWP controller

	HALT         : stop HWP 
	ENGA         : engage hwp software to a well known position
	CAL          : same as ENGA
	DEBUG        : run custom routine helper
	GOTO <pos>   : go to position (valid positions: 1 to 7)
	STEP <steps> : step motor (valid steps: 1 to 500)
	VEL          : set Ton and Toff times as VELOCITY for the square wave signal for the motor driver
	DIS          : disable motor
	EN           : enable motor
	DIR <dir>    : sets motor spin direction. Where <dir> is 0 (1-->7) and 1 (7-->1)
    
    '''
    cmd_noarg = cmd.split()[0]
    if cmd_noarg not in cmd_help.keys():
        show_hwp_help()
        return
    
    cmd_bytes = str.encode(cmd)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(cmd_bytes, (HWP_IP, CMD_PORT))
    s.close()
    return

def hwp_wait_for_arrival(pos,maxwait=60):
    '''
    wait for HWP to get to a particular position
    '''
    
    
    hwpinfo = get_hwp_info()
    if not hwpinfo['ok']:
        printmsg(hwpinfo['error_message'],'HWP',logfile=logfile)
        return hwpinfo
    
    is_arrived = hwpinfo['dir']=='STOPPED' and hwpinfo['pos']==pos

    if is_arrived:
        printmsg('HWP in position %s' % hwpinfo['pos'],'HWP',logfile=logfile)
        return hwpinfo

    start_time = utcnow()
    delta = utcnow() - start_time
    while not is_arrived and delta.total_seconds()<maxwait:
        sleep(1.85)
        hwpinfo = get_hwp_info()
        is_arrived = hwpinfo['dir']=='STOPPED' and hwpinfo['pos']==pos
        delta = utcnow() - start_time

    if not is_arrived:
        printmsg('ERROR! did not reach position %i: %s' % (pos,hwpinfo['error_message']),'HWP',logfile=logfile)
    
    printmsg('current position: %s' % hwpinfo['pos'],'HWP',logfile=logfile)
    return hwpinfo

def hwp_step_to_next_position(stepsize=10,direction=None,maxsteps=3720):
    '''
    take small steps until the next non-zero position

    direction: 0 is going from 1->7
    direction: 1 is going from 7->1
    
    '''    
    hwpinfo = get_hwp_info()
    if direction is None and hwpinfo['data message'].find('direction:')<0:
        print('HWP direction is not set.  Please specify a direction with option direction=0 or direction=1')
        return hwpinfo
    
    if direction is not None:
        send_hwp_command('DIR %i' % direction)
        
    stepcounter = 0
    while stepcounter<maxsteps:
        hwpinfo = get_hwp_info()
        pos = hwpinfo['pos']
        print('HWP position: %i, stepcounter: %i' % (pos,stepcounter))
        if pos!=0: break
        sleep(1)
        print('stepping %i' % stepsize)
        send_hwp_command('STEP %i' % stepsize)
        stepcounter += stepsize

    hwpinfo['stepcounter'] = stepcounter
    return hwpinfo



        

    
        
    
    


    
