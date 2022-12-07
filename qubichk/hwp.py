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
from qubichk.utilities import ping,shellcommand

QC_IP = "192.168.2.1"
HWP_IP = "192.168.2.100"
LISTEN_PORT = 5455


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
        s.bind((QC_IP, LISTEN_PORT))
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
        retval['error_message'] = 'motor not running'
        

    msg = 'HWP POS=%s, direction=%s, motor state=%s' % (pos_str,dir_str,motor_str)
    retval['brief message'] = msg
    retval['message'] = msg
    return retval



