#!/usr/bin/env python3
'''
$Id: ups.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 29 Nov 2021 17:13:16 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

a few methods to access info from the UPS
'''
import sys,os,time
import datetime as dt
from qubichk.utilities import shellcommand

def get_ups_info():
    '''
    get the UPS information
    '''
    battery_key = 'battery.status'
    voltage_key = 'input.voltage'

    log_parms = [voltage_key,
                 battery_key,
                 'battery.voltage',
                 'battery.runtime',
                 'ups.load']

    
    info = {}
    alarm = False
    
    cmd = 'upsc cyberpower'
    full_output,err = shellcommand(cmd)

    brief_msg_list = []
    log_msg_list = [dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')]
    lines = full_output.split('\n')
    for line in lines:
        col = line.split(':')
        if len(col)<2: continue
    
        parm = col[0].strip()
        val = col[1].strip()
        info[parm] = val
        
    if battery_key in info.keys():
        brief_msg_list.append('Battery level: %s' % info[battery_key])

    if voltage_key in info.keys():
        brief_msg_list.append('Input voltage: %s' % info[voltage_key])
        input_voltage = float(info[voltage_key])
        if input_voltage < 200: alarm = True

    if alarm:
        txtmsg = 'QUBIC is running on battery!\n'
    else:
        txtmsg = 'UPS status\n'

    txtmsg +=  '\n'.join(brief_msg_list)
    info['brief message'] = txtmsg
    txtmsg += '\n**************\n\nFull output from UPS:\n%s' % full_output

    info['alarm'] = alarm
    info['full message'] = txtmsg

    for parm in log_parms:
        if parm not in info.keys(): continue
        log_msg_list.append('%s=%s' % (parm,info[parm]))
            
    info['log message'] = ' '.join(log_msg_list)
    return info

 
    
    
