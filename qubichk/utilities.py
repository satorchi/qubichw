'''
$Id: utilities.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Sat 19 Nov 2022 11:48:03 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

utilities used by various modules in qubichk/hw especially hk_verify
'''
import subprocess,re,struct
import numpy as np

def shellcommand(cmd):
    '''
    run a shell command
    '''    
    proc = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out,err = proc.communicate()
    return out.decode().strip(),err.decode().strip()


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

def make_errmsg(msg=None):
    '''
    make an error message using all the sys exec info
    '''
    if msg is None:
        err_list = []
    else:
        err_list = [msg]
    for info in sys.exc_info():
        if info is not None:  err_list.append(str(info))            
    errormsg = ' \n'.join(err_list)
    return errormsg


fmt_translation={}
fmt_translation['uint8']   = 'B' 
fmt_translation['int8']    = 'b'
fmt_translation['int16']   = 'h'
fmt_translation['int32']   = 'i'
fmt_translation['int64']   = 'q'
fmt_translation['float32'] = 'f'
fmt_translation['float64'] = 'd'

fmt_reverse_translation = {}
for key in fmt_translation.keys():
    reverse_key = fmt_translation[key]
    fmt_reverse_translation[reverse_key] = key
    

def read_bindat(filename,names=None,fmt=None,STX=0xAA,verbosity=0):
    '''
    read the binary data saved to disk
    '''
    if not os.path.isfile(filename):
        print('ERROR!  File not found: %s' % filename)
        return None

    if names is None:
        print('Please give the names of the data record (comma separated list)')
        return None

    if fmt is None:
        print('Please give the format string (single character per item)')
        return None

    # determine the number of bytes per record entry
    fmt_list = []
    for idx in range(len(fmt)-1):
        fmt_list.append(fmt_reverse_translation[fmt[idx+1]])
    fmt_str = ','.join(fmt_list)    
    rec = np.recarray(names=names,formats=fmt_str,shape=(1))
    nbytes = rec.nbytes

    
    # read the data
    h = open(filename,'rb')
    bindat = h.read()
    h.close()

    # interpret the binary data
    names_list = names.split(',')
    data = {}
    for name in names_list:
        data[name] = []    

    idx = 0
    while idx+nbytes<len(bindat):
        packet = bindat[idx:idx+nbytes]
        dat_list = struct.unpack(fmt,packet)

        if len(dat_list)!=len(names_list):
            print('ERROR:  Incompatible data at byte %i' % idx)
            if verbosity>1: input('enter to continue ')
            idx += 1
            continue

        if dat_list[0]!=STX:
            print('ERROR: Incorrect data at byte %i' % idx)
            if verbosity>1: input('enter to continue ')
            idx += 1
            continue
            

        for datidx,name in enumerate(names_list):
            data[name].append(dat_list[datidx])
            if verbosity>0: print(dat_list)

        idx += nbytes

    for name in data.keys():
        data[name] = np.array(data[name])
        
    return data
