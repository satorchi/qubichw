#!/usr/bin/env python3
'''
$Id: hk_verify.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 12 Oct 2020 09:37:44 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

functions to check if QUBIC housekeeping is running
'''

import subprocess,re,os,sys,time
from glob import glob
import datetime as dt

from qubichw.compressor import compressor
from qubichk.send_telegram import send_telegram, get_alarm_recipients
from qubichk.ups import get_ups_info
from qubichk.hwp import get_hwp_info
from qubichw.energenie import *

alarm_recipients = get_alarm_recipients()

# list of machines on the housekeeping network
# the IP addresses are listed in /etc/hosts
machines = ['PiGPS',
            'qubicstudio',
            'hwp',
            'platform',
            'majortom',
            'horns',
            'mgc',
            'mmr',
            'pitemps']
#            'cam26'] # 2021-11-30 19:30:48 no cam26
#            'cam27'] # 2021-11-30 10:02:07 cam27 was never re-installed in Salta


def shellcommand(cmd):
    '''
    run a shell command
    '''
    
    proc = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out,err = proc.communicate()
    return out.decode(),err.decode()


def ping(machine,verbosity=1):
    '''
    ping a machine to make sure it's online
    '''
    retval = {}
    retval['machine'] = machine
    retval['ok'] = True
    retval['error_message'] = ''
    retval['message'] = ''

    msg = 'checking connection to %s...' % machine
    retval['message'] = msg
    if verbosity>0: print(msg, end='', flush=True)
    
    cmd = 'ping -c1 %s' % machine
    out,err = shellcommand(cmd)

    match = re.search('([0-9]*%) packet loss',out)
    if match is None:
        retval['ok'] = False
        msg = 'Could not determine network packet loss to %s' % machine
        retval['error_message'] = msg
        if verbosity>0: print('UNREACHABLE!\n--> %s' % msg)
        return retval

    packet_loss_str = match.groups()[0].replace('%','')
    packet_loss = float(packet_loss_str)

    if packet_loss > 99.0:
        retval['ok'] = False
        retval['error_message'] = 'unreachable'
        retval['message'] += 'UNREACHABLE'
        msg = 'UNREACHABLE!\n--> %s is unreachable.' % machine
        if machine=='modulator':
            msg += ' This is okay if Calsource is off.'
        else:
            msg += ' Please make sure it is switched on and connected to the housekeeping network'
        if verbosity>0: print(msg)
        return retval
    
    if packet_loss > 0.0:
        retval['ok'] = False
        retval['error_message'] = 'Unstable network'
        retval['message'] += 'UNREACHABLE'
        msg = 'ERROR!\n--> Unstable network to %s.' % machine
        msg += '  Please make sure the ethernet cable is well connected'
        if verbosity>0: print(msg)
        return retval

    retval['message'] += 'OK'
    if verbosity>0: print('OK')
    
    return retval
    

def check_network(verbosity=1,fulltest=False):
    '''
    ping the machines on the network
    '''
    retval = {}
    retval['ok'] = True
    retval['error_message'] = ''
    retval['message'] = ''
    errmsg_list = []
    msg_list = []
    if verbosity>0: print('\n============ checking network access ============')

    # before pinging all the machines, make sure the modulator is switched on
    if fulltest: # full test: switch on modulator
        calret = check_energenie_cal(modulator_state=True,verbosity=verbosity)
    else: # partial test: don't switch on modulator.  assume it's ok if Energenie is accessible
        calret = check_energenie_cal(modulator_state=False,verbosity=verbosity)
    if len(calret['message'])>0: msg_list.append(calret['message'])
    if len(calret['error_message'])>0: errmsg_list.append(calret['error_message'])
    states = calret['states']
    if states is None: retval['ok'] = False
    
    for machine in machines:
        retval[machine] = ping(machine,verbosity=verbosity)
        msg_list.append(retval[machine]['message'])
        if not retval[machine]['ok']:
            msg = '%s %s' % (machine,retval[machine]['error_message'])
            if machine=='modulator' and states is not None and not states[energenie_socket_number['modulator']]:
                msg += ' OK. Calsource is OFF'
            else:
                retval['ok'] = False
            errmsg_list.append(msg)

    if fulltest and states is not None and not states[energenie_socket_number['modulator']]: # switch off the modulator again
        msg = 'switching off modulator after the ping'
        if verbosity>0: print(msg)
        info = energenie_cal_set_socket_states(states)
        msg_list.append(msg)
        msg_list.append(info['message'])

    if len(errmsg_list)>0: retval['error_message'] += '\n  '.join(errmsg_list)
    retval['message'] = '\n'.join(msg_list)
    return retval

def check_power(verbosity=1):
    '''
    check if the components attached to the Energenie power bar are switched on
    '''
    retval = {}
    retval['ok'] = True
    retval['error_message'] = ''
    retval['message'] = ''
    errmsg_list = []
    msg_list = []
    if verbosity>0: print('\n============ checking for power connections ============')

    energenie_manager = 'sispmctl'
    
    # check that the Energenie manager application is installed
    cmd = 'which %s' % energenie_manager
    out,err = shellcommand(cmd)
    if out=='':
        retval['ok'] = False
        retval['error_message'] = '%s application not found.' % energenie_manager
        msg = 'ERROR! %s\n--> Please install the application at http://sispmctl.sourceforge.net' % retval['error_message']
        retval['message'] = msg
        if verbosity>0: print(msg)
        return retval


    # try a few times to connect to the Energenie USB powerbar
    error_counter = 0
    max_count = 3
    match = None
    find_str = '(Status of outlet [1-4]:\t)(off|on)'
    cmd = 'sispmctl -g all'
    while match is None and error_counter<max_count:
        out,err = shellcommand(cmd)
        match = re.search(find_str,out)
        if match is None:
            error_counter += 1
            retval['error_message'] = 'USB Energenie powerbar not detected: error count=%i' % error_counter
            if err: retval['error_message'] += '\n'+err
            if out: retval['error_message'] += '\n'+out
            msg =  retval['error_message']
            retval['message'] = msg
            if verbosity>0: print(msg)
            if error_counter<max_count: time.sleep(3)

    if match is None:
        retval['ok'] = False
        msg = 'ERROR! %s\n-->Please check USB connection' % retval['error_message']
        if verbosity>0: print(msg)    
        return retval
            
    for socket in energenie_socket.keys():
        find_str = '(Status of outlet %i:\t)(off|on)' % socket
        match = re.search(find_str,out)
        if match is None:
            retval['ok'] = False
            msg = 'Could not find Energenie power status for %s' % energenie_socket[socket]
            retval['error_message'] = msg
            retval['message'] = msg
            if verbosity>0: print('\nERROR! %s' % msg)
            return retval

        subsys = energenie_socket[socket]
        state = match.groups()[1]
        retval[subsys] = state
        msg = '%s is %s' % (subsys,state)
        msg_list.append(msg)
        if state=='off':
            retval['ok'] = False
            errmsg_list.append(msg)
            msg += '\n--> Please switch on %s with the command "qubic_poweron" (no quotes)' % subsys
        else:
            msg += '... OK'
        if verbosity>0: print(msg)

    if len(errmsg_list)>0:
        retval['error_message'] = '\n  '.join(errmsg_list)
    retval['message'] = '\n'.join(msg_list)
    return retval
    

def check_mounts(verbosity=1):
    '''
    check for remote mounted disks (Major Tom and QubicStudio)
    '''
    retval = {}
    retval['ok'] = True
    retval['error_message'] = ''
    msg_list = []
    errmsg_list = []

    if verbosity>0: print('\n============ checking for remote disk shares ============')
    smbmounts = ['qs','entropy']
    smbmounts = ['entropy'] # qs is mounted on pitemps
    cmd = 'mount'
    out,err = shellcommand(cmd)
    ### 2021-11-30 09:58:50 new config.  qs is mounted directly on qubic-central again
    # # qs2 is mounted on pitemps because of a bug with Windows mounts on qubic-central
    # cmd = 'ssh pitemps mount'
    # out2,err = shellcommand(cmd)
    # out = out1+'\n'+out2
    find_str = '(%s) type cifs' % '|'.join(smbmounts)
    match = re.findall(find_str,out)
    for smbshare in match:
        retval[smbshare] = 'ok'
        msg = '%s... OK' % smbshare
        if verbosity>0: print(msg)
        msg_list.append(msg)

    if len(match)<len(smbmounts):
        for smbshare in smbmounts:
            if smbshare not in retval.keys():
                retval['ok'] = False
                retval[smbshare] = 'missing'
                msg = 'ERROR! Missing Windows mount: %s' % smbshare
                errmsg_list.append(msg)
                if verbosity>0: print(msg)
                
                
    if len(errmsg_list)>0:
        retval['error_message'] += '\n  '.join(errmsg_list)
    retval['message'] = '\n'.join(msg_list)
    return retval

def check_diskspace(verbosity=1):
    '''
    check for sufficient disk space
    '''
    retval = {}
    retval['ok'] = True
    retval['error_message'] = ''
    msg_list = []
    errmsg_list = []
    
    space_warning = 10*1024**2 # 10GB minimum disk space (df gives results in 1k blocks)
    if verbosity>0: print('\n============ checking for disk space ============')
    parts = ['home','archive','entropy','qs2']
        
    find_str = '/'+'|/'.join(parts)
    
    cmd = 'df'
    out1,err = shellcommand(cmd)
    # 2021-11-30 10:00:02 qs is mounted directly on qubic-central again
    # 2022-02-23 16:38:02 qs is back to pitemps... same bug
    # qs2 is mounted on pitemps because of a bug with Windows mounts on qubic-central
    cmd = 'ssh pitemps df'
    out2,err = shellcommand(cmd)
    out = out1+'\n'+out2
    for line in out.split('\n'):
        cols = line.split()
        if len(cols)==0: continue
        disk_info = {}
        match = re.search(find_str,cols[-1])
        if match:
            tot_space = int(cols[1])
            used_space = int(cols[2])
            remain_space = int(cols[3])
            mount_dir = cols[-1]
            part = mount_dir.replace('/','')

            remain_gb = remain_space/1024**2

            disk_info['total'] = tot_space
            disk_info['used'] = used_space
            disk_info['available'] = remain_space
            disk_info['dir'] = mount_dir

            msg = '%s has %.1fGB available space' % (mount_dir,remain_gb)
            if remain_space < space_warning:
                msg += '\n-->WARNING! Risk of running out of space!'
                retval['ok'] = False
                errmsg_list.append(msg)
            msg_list.append(msg)
            if verbosity>0: print(msg)
            
            retval[part] = disk_info

    for part in parts:
        if part not in retval.keys():
            retval['ok'] = False
            msg = 'ERROR! Could not find "%s"' % part
            errmsg_list.append(msg)
            msg += '\n--> Please investigate.  You should probably run the command "mount /%s" (no quotes)' % part
            if verbosity>0: print(msg)
            disk_info['total'] = 0
            disk_info['used'] = 0
            disk_info['available'] = 0
            disk_info['dir'] = '/'+part
            retval[part] = disk_info

    if len(errmsg_list)>0:
        retval['error_message'] += '\n  '.join(errmsg_list)
    retval['message'] = '\n'.join(msg_list)
    return retval

def check_servers(verbosity=1):
    '''
    check that the housekeeping server is running
    check that the bot is running
    '''
    retval = {}
    retval['ok'] = True
    retval['error_message'] = ''
    msg_list = []
    errmsg_list = []
    start_command = {}
    start_command['run_hkserver.py'] = 'start_hkserver.sh'
    start_command['run_bot.py'] = 'start_bot.sh'

    if verbosity>0: print('\n============ checking housekeeping daemons')
    cmd = 'ps axwu'
    out,err = shellcommand(cmd)

    for daemon in start_command.keys():
        if verbosity>0: print('%s ...' % daemon,end='',flush=True)
        find_str = 'python.*%s' % daemon
        match = re.search(find_str,out)
        if match is None:
            retval['ok'] = False
            msg = 'not running'
            if verbosity>0: print(msg)
            errmsg_list.append('%s %s' % (daemon,msg))
            retval[daemon] = msg
            if verbosity>0: print('\n--> Please run the command "%s" (no quotes)' % start_command[daemon])
        else:
            msg = 'OK'
            if verbosity>0: print(msg)
            retval[daemon] = msg
        msg_list.append('%s %s' % (daemon,msg))
            
    retval['message'] = '\n'.join(msg_list)
    if len(errmsg_list)>0: retval['error_message'] = '\n  '.join(errmsg_list)
    return retval


def check_temps(verbosity=1):
    '''
    check that the most recent recorded housekeeping are from now
    '''
    retval = {}
    retval['ok'] = True
    retval['error_message'] = ''
    msg_list = []
    # 2021-11-30 10:32:42 where did this number come from?  
    # nfiles = 47 # total number expected.
    # 8 channels on AVS47_1
    # 5 channels on AVS47_2
    # 2 MHS
    # 12 for 6 heaters (voltage and current) There used to be 7 heaters
    # 18 temperature sensors
    # 1 pressure sensor
    nfiles = 46    
    delta_max = 6 # seconds. if latest HK is earlier than this, we have a problem
    if verbosity>0: print('\n============ checking recent housekeeping values...',end='',flush=True)
    hk_dir = '/home/qubic/data/temperature/broadcast'

    patterns = ['TEMPERATURE??.txt','AVS47*.txt','MHS*.txt','HEATER*.txt','PRESSURE*.txt']

    hk_files = []
    for pattern in patterns:
        glob_pattern =  '%s/%s' % (hk_dir,pattern)
        hk_files.extend(glob(glob_pattern))

    hk_files.sort()
    if len(hk_files)<nfiles:
        retval['ok'] = False
        msg = 'missing HK data files.  Found %i out of %i.' % (len(hk_files),nfiles)
        if verbosity>0: print('\nERROR! %s' % msg)
        retval['error_message'] += msg

    for F in hk_files:
        info = {}
        info['name'] = os.path.basename(F)
        info['ok'] = True
        h = open(F,'rb')
        h.seek(0,os.SEEK_END)
        fsize = h.tell()
        if fsize<29:
            info['ok'] = False
            retval['ok'] = False
            info['error_message'] = 'file too small: %s' % info['name']
            msg = 'unable to read timestamp. File too smalle %s' % info['name']
            if verbosity>0: print('\nERROR! %s' % msg,end='')
            retval['error_message'] += msg
            retval[F] = info
            continue

            
        h.seek(-29,os.SEEK_END)
        x = h.read()
        h.close()
        lines = x.decode().split('\n')
        lastline = lines[-2]
        try:
            tstamp = float(lastline.split()[0])
        except:
            info['ok'] = False
            retval['ok'] = False
            info['error_message'] = 'unable to read timestamp'
            msg = 'unable to read timestamp for %s' % info['name']
            if verbosity>0: print('\nERROR! %s' % msg,end='')
            retval['error_message'] += msg
            retval[F] = info
            continue

        now = dt.datetime.utcnow()
        tstamp_now = float(now.strftime('%s.%f'))
        delta = tstamp_now - tstamp
        if delta > delta_max:
            info['ok'] = False
            retval['ok'] = False
            msg = 'too long since last data for %s: %f seconds' % (info['name'],delta)
            if verbosity>0: print('\nERROR! %s' % msg,end='')
            retval['error_message'] += '\n'+msg

        retval[info['name']] = info

    if retval['ok']:
        retval['message'] = 'housekeeping values ... OK'
        if verbosity>0: print('OK')
    else:
        retval['message'] = 'housekeeping values ... ERROR!'
    return retval

def check_calsource(verbosity=1):
    '''
    check that the calibration source manager is running on PiGPS
    check that the calibration source broadcaster is running on PiGPS
    '''
    retval = {}
    retval['ok'] = True
    retval['error_message'] = ''
    start_command = {}
    start_command['calsource_commander.py'] = 'start_calsource_manager.sh'
    start_command['read_calsource.py'] = 'start_calsource_acq.sh'
    start_command['gpsd'] = 'gpsd'
    start_command['ntpd'] = 'ntpd'

    if verbosity>0: print('\n============ checking calsource daemons ============')
    cmd = 'ssh pigps ps axwu'
    out,err = shellcommand(cmd)
    if len(out)==0:
        msg = 'ERROR! Could not connect to PiGPS'
        retval['message'] = msg
        retval['error_message'] = msg
        msg += '\n--> Please check network connections'
        if verbosity>0: print(msg)
        for daemon in start_command.keys():
            retval[daemon] = 'could not connect'
        return retval
        
    msg_list = []
    errmsg_list = []
    for daemon in start_command.keys():
        msg = '%s ...' % daemon
        if verbosity>0: print(msg,end='',flush=True)
        if daemon.find('.py')>0:
            find_str = 'python.*%s' % daemon
        else:
            find_str = daemon
        match = re.search(find_str,out)
        if match is None:
            retval['ok'] = False
            if verbosity>0: print('not running')
            msg += 'not running'
            errmsg_list.append(msg)
            retval[daemon] = 'not running'
            if verbosity>0: print('\n--> Please log onto PiGPS and run the command "%s" (no quotes)' % start_command[daemon])
        else:
            if verbosity>0: print('OK')
            msg += 'OK'
            retval[daemon] = msg
        msg_list.append(msg)

            
    retval['message'] = '\n'.join(msg_list)
    if len(errmsg_list)>0: retval['error_message'] = '\n  '.join(errmsg_list)
    
    return retval

def check_compressors(verbosity=1):
    '''
    check the status of the pulse tube compressors
    '''
    retval = {}
    retval['ok'] = True
    retval['communication error'] = False
    retval['error_message'] = ''
    retval['message'] = ''
    
    if verbosity>0: print('\n============ checking pulse tube compressors ============')

    msg_list = []
    errmsg_list = []
    for c_num in range(1,3):
        c = compressor(c_num)
        info = c.status()
        msg_list.append('\nCompressor %s' % c_num)
        msg_list.append(info['status_message'])
        if not info['status']:
            retval['ok'] = False
            retval['communication error'] = info['communication error']
            errmsg_list.append('\nCompressor %s' % c_num)
            errmsg_list.append(info['msg'])
            
    if len(errmsg_list)>0: retval['error_message'] = '\n  '.join(errmsg_list)
    retval['message'] = '\n  '.join(msg_list)
    if verbosity>0: print(retval['message'])
    return retval

def check_ups(verbosity=1):
    '''
    check the UPS
    '''
    if verbosity>0: print('\n============ checking UPS ============')
    retval = {}
    info = get_ups_info()
    retval['ok'] =  not info['alarm']
    retval['message'] = info['brief message']
    if verbosity>0: print(retval['message'])
    return retval

def check_hwp(verbosity=1):
    '''
    get the HWP position
    '''
    if verbosity>0: print('\n============ checking HWP ============')
    retval = get_hwp_info()
    if verbosity>0: print(retval['message'])
        
    return retval

def hk_ok(verbosity=1,fulltest=False):
    '''
    check that housekeeping is okay
    '''
    retval = {}
    ok = True
    message = ''

    retval['ups'] = check_ups(verbosity=verbosity)
    retval['power'] = check_power(verbosity=verbosity)
    retval['network'] = check_network(verbosity=verbosity,fulltest=fulltest)
    retval['mounts'] = check_mounts(verbosity=verbosity)
    retval['diskspace'] = check_diskspace(verbosity=verbosity)
    retval['calsource'] = check_calsource(verbosity=verbosity)
    retval['hwp'] = check_hwp(verbosity=verbosity)
    retval['servers'] = check_servers(verbosity=verbosity)
    retval['temps'] = check_temps(verbosity=verbosity)
    retval['compressor'] = check_compressors(verbosity=verbosity)

    message_list = []
    for key in retval.keys():        
        if 'ok' not in retval[key].keys():
            if verbosity>0: print('missing ok key for %s' % key)
            continue
        if not retval[key]['ok']:
            ok = False
            if 'error_message' not in retval[key].keys():
                message += '\n%s: no message' % key
            else:
                message += '\n%s:\n  %s' % (key,retval[key]['error_message'])

        
        message_list.append('============= %s ================' % key)
        message_list.append(retval[key]['message'])


    if not ok:
        ttl =  '\n*******************************'
        ttl += '\n* QUBIC Housekeeping problems *'
        message_list.append(ttl)
        message_list.append(message)
        if verbosity>0: print(ttl)
        if verbosity>0: print(message)
        errmsg = ttl+'\n'+message
        send_telegram(errmsg)
        
    retval['error_message'] = message
    retval['ok'] = ok

    full_message = '\n'.join(message_list)
    retval['full_message'] = full_message
    
    return retval

