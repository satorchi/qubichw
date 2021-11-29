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
import sys,os,time,subprocess
import datetime as dt

def get_ups_info():
    '''
    get the UPS information
    '''
    log_parms = ['input.voltage',
                 'battery.charge',
                 'battery.voltage',
                 'battery.runtime',
                 'ups.load']

    brief_parms = ['battery.charge',
                   'intput.voltage']
    
    info = {}
    alarm = False
    
    cmd = 'upsc cyberpower'
    proc = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out,err = proc.communicate()
    full_output = out.decode()

    brief_msg_list = []
    log_msg_list = [dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')]
    lines = full_output.split('\n')
    for line in lines:
        col = line.split(':')
        if len(col)<2: continue
    
        parm = col[0].strip()
        val = col[1].strip()
        info[parm] = val
        
    if 'battery.charge' in info.keys():
        brief_msg_list.append('Battery level: %s' % info['battery.charge'])

    if 'input.voltage' in info.keys():
        brief_msg_list.append('Input voltage: %s' % info['input.voltage'])
        input_voltage = float(info['input.voltage'])
        if input_voltage < 200: alarm = True

    if alarm:
        txtmsg = 'QUBIC is running on battery!\n'
    else:
        txtmsg = 'UPS status\n'

    txtmsg +=  '\n'.join(brief_msg_list)
    txtmsg += '\n**************\n\nFull output from UPS:\n%s' % full_output

    info['alarm'] = alarm
    info['full message'] = txtmsg

    for parm in log_parms:
        if parm not in info.keys(): continue
        log_msg_list.append('%s=%s' % (parm,info[parm]))
            
    info['log message'] = ' '.join(log_msg_list)
    return info

 
    
    
