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
import socket,re
from qubichk.utilities import ping,shellcommand,get_myip,get_known_hosts

known_hosts = get_known_hosts()
QC_IP = known_hosts['qubic-central']
HWP_IP = known_hosts['hwp']
MY_IP = get_myip()
LISTEN_PORT = 5455
CMD_PORT = 5454


def get_hwp_info():
    '''
    get the current position and direction of the HWP
    '''
    retval = {}
    retval['ok'] = False

    # check if hwp is responding
    ping_result = ping(HWP_IP,verbosity=0)
    if not ping_result['ok']:
        retval['ok'] = False
        retval['message'] = 'HWP is not responding on the network'
        retval['error_message'] = retval['message']
        retval['brief message'] = 'HWP unavailable'
        retval['pos'] = None
        retval['dir'] = None
        retval['motor'] = None
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
        retval['pos'] = None
        retval['dir'] = None
        retval['motor'] = None
        return retval
        
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1)
    try:
        s.bind((MY_IP, LISTEN_PORT))
        msg_ack = "cmd received"
        msg_bytes = msg_ack.encode()
        msg_rcv, addr = s.recvfrom(1024)
        s.close()
    except:
        retval['ok'] = False
        retval['message'] = 'HWP info unavailable: socket in use.  Try again.'
        retval['error_message'] = 'HWP info unavailable: socket in use.'
        retval['brief message'] = retval['message']
        retval['pos'] = None
        retval['dir'] = None
        retval['motor'] = None
        return retval
    
    msg = msg_rcv.decode()
    if msg.find('motor not running')>0:
        motor_str = 'motor not running'
        pos_str = msg.split('motor')[0].split()[1]
        dir_str = 'STOPPED'
    else:        
        pos_str = msg.split('direction')[0].split()[1]
        dir_str = msg.split('direction:')[1].split(',')[0].strip()
        motor_str = msg.split(',')[-1].strip()

    retval['pos'] = pos_str
    retval['dir'] = dir_str
    retval['motor'] = motor_str
    if motor_str=='motor running':
        retval['ok'] = True
    else:
        retval['ok'] = False
        retval['error_message'] = motor_str
        

    msg = 'HWP POS=%s, direction=%s, motor state=%s' % (pos_str,dir_str,motor_str)
    retval['brief message'] = msg
    retval['message'] = msg
    return retval

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

def show_hwp_help():
    '''
    print a help text
    '''
    for cmd in cmd_help.keys():
        print('%s: %s' % (cmd.ljust(8),valid_commands))
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
    s = socket.socket(socket.AF_INET, socket`.SOCK_DGRAM)
    s.sendto(cmd_bytes, (HWP_IP, CMD_PORT))
    s.close()
    return




    
