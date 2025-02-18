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

def get_fullpath(filename=None):
    '''
    get the full path to the desired file
    usually it's in the .local/share/qubic directory
    filename might be botId.txt, telegram_addressbook, powersupply.conf, calbox.conf, whatever...
    '''
    search_dirs = []
    if 'XDG_DATA_HOME' in os.environ.keys():
        search_dirs.append('%s/qubic' % os.environ['XDG_DATA_HOME'])
    if 'HOME' in os.environ.keys():
        homedir = os.environ['HOME']        
    else:
        homedir = '/home/qubic'
    search_dirs.append('%s/.local/share/qubic' % homedir)
    search_dirs.append('./')
    search_dirs.append('/home/qubic/.local/share/qubic')

    for d in search_dirs:
        fullpath = '%s/%s' % (d,filename)
        if os.path.isfile(fullpath):
            return fullpath

    return None

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


def read_conf_file(filename):
    '''
    read some parameters from a configuration file
    used for calsource box, but maybe will be implemented for other things
    '''
    if not os.path.isfile(filename):
        print('ERROR! File not found: %s' % filename
        return None

    h = open(filename,'r')
    lines = h.read().split('\n')
    h.close()

    
