#!/usr/bin/env python3
'''
$Id: hk_ok.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 12 Oct 2020 09:37:44 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

check if QUBIC housekeeping is running
'''

import subprocess,re,os
from glob import glob
import datetime as dt

from qubichw.compressor import compressor
from qubichk.send_telegram import send_telegram

# list of machines on the housekeeping network
# the IP addresses are listed in /etc/hosts
machines = ['PiGPS','qubicstudio','hwp','platform','energenie','majortom','horns','modulator','mgc','mmr','pitemps']

# list of sockets in the Energenie powerbar on the housekeeping electronics rack
# also called the "Remote Controlled Power Bar 2" (RCPB2) in Emiliano's wiring diagram
energenie = {}
energenie[1] = 'horn'
energenie[2] = 'heaters'
energenie[3] = 'hwp'
energenie[4] = 'thermos'

def shellcommand(cmd):
    '''
    run a shell command
    '''
    
    proc = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out,err = proc.communicate()
    return out.decode(),err.decode()


def ping(machine):
    '''
    ping a machine to make sure it's online
    '''
    retval = {}
    retval['machine'] = machine
    retval['ok'] = True
    retval['message'] = 'unknown'
    
    print('checking connection to %s...' % machine, end='', flush=True)
    
    cmd = 'ping -c1 %s' % machine
    out,err = shellcommand(cmd)

    match = re.search('([0-9]*%) packet loss',out)
    if match is None:
        retval['ok'] = False
        msg = 'Could not determine network packet loss to %s' % machine
        retval['message'] = msg
        print('ERROR!\n--> %s' % msg)
        return retval

    packet_loss_str = match.groups()[0].replace('%','')
    packet_loss = float(packet_loss_str)

    if packet_loss > 99.0:
        retval['ok'] = False
        retval['message'] = 'unreachable'
        msg = 'ERROR!\n--> %s is unreachable.' % machine
        if machine=='modulator':
            msg += ' This is okay if Calsource is off.'
        else:
            msg += ' Please make sure it is switched on and connected to the housekeeping network'
        print(msg)
        return retval
    
    if packet_loss > 0.0:
        retval['ok'] = False
        retval['message'] = 'Unstable network'
        msg = 'ERROR!\n--> Unstable network to %s.' % machine
        msg += '  Please make sure the ethernet cable is well connected'
        print(msg)
        return retval

    msg = 'OK'
    retval['message'] = msg
    print(msg)
    
    return retval


def check_network():
    '''
    ping the machines on the network
    '''
    retval = {}
    retval['ok'] = True
    retval['message'] = ''
    msg_list = []
    print('\n============ checking network access ============')

    for machine in machines:
        retval[machine] = ping(machine)
        if not retval[machine]['ok']:
            retval['ok'] = False
            msg = '%s %s' % (machine,retval[machine]['message'])
            if machine=='modulator':
                msg += ' OK if Calsource is OFF'
            msg_list.append(msg)


    if len(msg_list)>0:
        retval['message'] += ' | '.join(msg_list)
    return retval

def check_power():
    '''
    check if the components attached to the Energenie power bar are switched on
    '''
    retval = {}
    retval['ok'] = True
    retval['message'] = ''
    errmsg_list = []
    print('\n============ checking for power connections ============')

    energenie_manager = 'sispmctl'
    
    # check that the Energenie manager application is installed
    cmd = 'which %s' % energenie_manager
    out,err = shellcommand(cmd)
    if out=='':
        retval['ok'] = False
        retval['message'] = '%s application not found.' % energenie_manager
        msg = 'ERROR! %s\n--> Please install the application at http://sispmctl.sourceforge.net' % retval['message']
        return retval
        
    cmd = 'sispmctl -g all'
    out,err = shellcommand(cmd)
        
    for socket in energenie.keys():
        find_str = '(Status of outlet %i:\t)(off|on)' % socket
        match = re.search(find_str,out)
        if match is None:
            retval['ok'] = False
            retval['message'] = 'Energenie powerbar not detected'
            msg = 'ERROR! %s\n-->Please check USB connection'
            return retval

        subsys = energenie[socket]
        state = match.groups()[1]
        retval[subsys] = state
        msg = '%s is %s' % (subsys,state)
        if state=='off':
            retval['ok'] = False
            errmsg_list.append(msg)
            msg += '\n--> Please switch on %s with the command "qubic_poweron" (no quotes)' % subsys
        else:
            msg += '... OK'
        print(msg)

    if len(errmsg_list)>0:
        retval['message'] = ' | '.join(errmsg_list)
    return retval
    

def check_mounts():
    '''
    check for remote mounted disks (Major Tom and QubicStudio)
    '''
    retval = {}
    retval['ok'] = True
    retval['message'] = ''
    print('\n============ checking for remote disk shares ============')
    smbmounts = ['qs2','entropy']
    cmd = 'mount'
    out1,err = shellcommand(cmd)
    # qs2 is mounted on pitemps because of a bug with Windows mounts on qubic-central
    cmd = 'ssh pitemps mount'
    out2,err = shellcommand(cmd)
    out = out1+'\n'+out2
    find_str = '(%s) type cifs' % '|'.join(smbmounts)
    match = re.findall(find_str,out)
    for smbshare in match:
        retval[smbshare] = 'ok'
        print('%s... OK' % smbshare)

    errmsg_list = []
    if len(match)<len(smbmounts):
        for smbshare in smbmounts:
            if smbshare not in retval.keys():
                retval['ok'] = False
                retval[smbshare] = 'missing'
                msg = 'ERROR! Missing Windows mount: %s' % smbshare
                errmsg_list.append(msg)
                print(msg)
                
                
    if len(errmsg_list)>0:
        retval['message'] += '\n'.join(errmsg_list)
    return retval

def check_diskspace():
    '''
    check for sufficient disk space
    '''
    retval = {}
    retval['ok'] = True
    retval['message'] = ''
    space_warning = 10*1024**2 # 10GB minimum disk space (df gives results in 1k blocks)
    print('\n============ checking for disk space ============')
    parts = ['home','archive','entropy','qs2']
        
    find_str = '/'+'|/'.join(parts)
    
    cmd = 'df'
    out1,err = shellcommand(cmd)
    # qs2 is mounted on pitemps because of a bug with Windows mounts on qubic-central
    cmd = 'ssh pitemps df'
    out2,err = shellcommand(cmd)
    out = out1+'\n'+out2
    msg_list = []
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
                msg_list.append(msg)
            print(msg)
            
            retval[part] = disk_info

    for part in parts:
        if part not in retval.keys():
            retval['ok'] = False
            msg = 'ERROR! Could not find "%s"' % part
            msg_list.append(msg)
            msg += '\n--> Please investigate.  You should probably run the command "mount /%s" (no quotes)' % part
            print(msg)
            disk_info['total'] = 0
            disk_info['used'] = 0
            disk_info['available'] = 0
            disk_info['dir'] = '/'+part
            retval[part] = disk_info

    if len(msg_list)>0:
        retval['message'] += '\n'.join(msg_list)
    return retval

def check_servers():
    '''
    check that the housekeeping server is running
    check that the bot is running
    '''
    retval = {}
    retval['ok'] = True
    retval['message'] = ''
    start_command = {}
    start_command['run_hkserver.py'] = 'start_hkserver.sh'
    start_command['run_bot.py'] = 'start_bot.sh'

    print('\n============ checking housekeeping daemons')
    cmd = 'ps axwu'
    out,err = shellcommand(cmd)

    for daemon in start_command.keys():
        print('%s ...' % daemon,end='',flush=True)
        find_str = 'python.*%s' % daemon
        match = re.search(find_str,out)
        if match is None:
            retval['ok'] = False
            msg = 'not running'
            retval['message'] += ' %s %s' % (daemon,msg)
            retval[daemon] = msg
            msg += '\n--> Please run the command "%s" (no quotes)' % start_command[daemon]
            print(msg)
        else:
            msg = 'OK'
            retval[daemon] = msg
            print(msg)
            
    
    return retval


def check_temps():
    '''
    check that the most recent recorded housekeeping are from now
    '''
    retval = {}
    retval['ok'] = True
    retval['message'] = ''
    nfiles = 47 # total number expected
    delta_max = 6 # seconds. if latest HK is earlier than this, we have a problem
    print('\n============ checking recent housekeeping values...',end='',flush=True)
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
        print('\nERROR! %s' % msg)
        retval['message'] += msg

    for F in hk_files:
        info = {}
        info['name'] = os.path.basename(F)
        info['ok'] = True
        h = open(F,'rb')
        h.seek(-80,os.SEEK_END)
        x = h.read()
        h.close()
        lines = x.decode().split('\n')
        lastline = lines[-2]
        try:
            tstamp = float(lastline.split()[0])
        except:
            info['ok'] = False
            retval['ok'] = False
            info['message'] = 'unable to read timestamp'
            msg = 'unable to read timestamp for %s' % info['name']
            print('\nERROR! %s' % msg,end='')
            retval['message'] += msg
            retval[F] = info
            continue

        now = dt.datetime.utcnow()
        tstamp_now = float(now.strftime('%s.%f'))
        delta = tstamp_now - tstamp
        if delta > delta_max:
            info['ok'] = False
            retval['ok'] = False
            msg = 'too long since last data for %s: %f seconds' % (info['name'],delta)
            print('\nERROR! %s' % msg,end='')
            retval['message'] += '\n'+msg

        retval[info['name']] = info

    if retval['ok']: print('OK')
    return retval

def check_calsource():
    '''
    check that the calibration source manager is running on PiGPS
    check that the calibration source broadcaster is running on PiGPS
    '''
    retval = {}
    retval['ok'] = True
    retval['message'] = ''
    start_command = {}
    start_command['calsource_commander.py'] = 'start_calsource_manager.sh'
    start_command['read_calsource.py'] = 'start_calsource_acq.sh'

    print('\n============ checking calsource daemons ============')
    cmd = 'ssh pigps ps axwu'
    out,err = shellcommand(cmd)
    if len(out)==0:
        msg = 'ERROR! Could not connect to PiGPS'
        msg += '\n--> Please check network connections'
        print(msg)
        for daemon in start_command.keys():
            retval[daemon] = 'could not connect'
        return retval
        
    
    for daemon in start_command.keys():
        print('%s ...' % daemon,end='',flush=True)
        find_str = 'python.*%s' % daemon
        match = re.search(find_str,out)
        if match is None:
            msg = 'not running'
            retval[daemon] = msg
            msg += '\n--> Please log onto PiGPS and run the command "%s" (no quotes)' % start_command[daemon]
            print(msg)
        else:
            msg = 'OK'
            retval[daemon] = msg
            print(msg)
            
        
    
    return retval

def check_compressors():
    '''
    check the status of the pulse tube compressors
    '''
    retval = {}
    retval['ok'] = True
    retval['message'] = ''
    print('\n============ checking pulse tube compressors ============')

    msg_list = []
    errmsg_list = []
    for c_num in range(1,3):
        c = compressor(c_num)
        info = c.status()
        msg_list.append('\nCompressor %s' % c_num)
        msg_list.append(c.status_message())
        if not info['status']:
            retval['ok'] = False
            
    if len(msg_list)>0: retval['message'] = '\n'.join(msg_list)
    print(retval['message'])
    return retval

def hk_ok():
    '''
    check that housekeeping is okay
    '''
    retval = {}
    ok = True
    message = ''

    retval['power'] = check_power()
    retval['network'] = check_network()
    retval['mounts'] = check_mounts()
    retval['diskspace'] = check_diskspace()
    retval['calsource'] = check_calsource()
    retval['servers'] = check_servers()
    retval['temps'] = check_temps()
    retval['compressor'] = check_compressors()

    message_list = []
    for key in retval.keys():        
        if 'ok' not in retval[key].keys():
            print('missing ok key for %s' % key)
            continue
        if not retval[key]['ok']:
            ok = False
            if 'message' not in retval[key].keys():
                message += '\n%s: no message' % key
            else:
                message += '\n%s: %s' % (key,retval[key]['message'])
        message_list.append('============= %s ================' % key)
        message_list.append(retval[key]['message'])


    if not ok:
        ttl = '\n***************** There were problems/warnings ****************'
        message_list.append(ttl)
        message_list.append(message)
        print(ttl)
        print(message)
    retval['message'] = message
    retval['ok'] = ok

    full_message = '\n'.join(message_list)
    send_telegram(full_message)
    
    return retval

if __name__=='__main__':
    ret = hk_ok()
    
