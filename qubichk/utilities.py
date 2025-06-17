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
import sys,os,subprocess,re,struct

# QUBIC position from PiGPS (antenna on the mount)
qubic_latitude = -(24 + 11.2002/60)
qubic_longitude = -(66 + 28.7039/60)

known_hosts = {}
known_hosts['qubic-central'] = "192.168.2.1"
known_hosts['qubic-studio']  = "192.168.2.113"
known_hosts['calsource']     = "192.168.2.5"
known_hosts['pigps']         = "192.168.2.17"
known_hosts['redpitaya']     = "192.168.2.21"
known_hosts['groundgps']     = "192.168.2.22"
known_hosts['horn']          = "192.168.2.9"

date_logfmt = '%Y-%m-%d %H:%M:%S UT'

hk_dir = '/home/qubic/data/temperature/broadcast'
fridge_dir = '/home/qubic/data/temperature'

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
        print('ERROR! File not found: %s' % filename)
        return None

    h = open(filename,'r')
    lines = h.read().split('\n')
    h.close()

    config = {}
    section = None
    for line in lines:
        if len(line)==0: continue
        if line[0]=='#': continue
        # remove comments
        line = line.strip().split('#')[0].strip()
        if len(line)==0: continue

        if line[0]=='[':
              section = line.strip().replace('[','').replace(']','').lower()
              continue

        if section is None: continue

        if section not in config.keys():
              config[section] = []
        
        config[section].append(line)

    return config
              

def get_receiver_list(conf_file='calbox.conf'):
    '''
    read the list of receivers from the config file (eg. calbox.conf)
    '''
    conf_file_fullpath = get_fullpath(conf_file)
    if conf_file_fullpath is None:
        print('Default receiver is qubic-central: %s' % known_hosts['qubic-central'])
        return [known_hosts['qubic-central']]

    conf = read_conf_file(conf_file_fullpath)

    if 'receivers' not in conf.keys():
        print('No Receiver section in configuration file: %s' % conf_file_fullpath)
        print('Default receiver is qubic-central: %s' % known_hosts['qubic-central'])
        return [known_hosts['qubic-central']]

    return conf['receivers']

def get_calsource_host(conf_file='calbox.conf'):
    '''
    get the IP address of the calsource configuration manager
    it's written in calbox.conf configuration file, otherwise use the default from known_hosts
    '''
    conf_file_fullpath = get_fullpath(conf_file)
    if conf_file_fullpath is None:
        print('Default calsource manager is calsource: %s' % known_hosts['calsource'])
        return known_hosts['calsource']

    conf = read_conf_file(conf_file_fullpath)

    if 'manager' not in conf.keys():
        print('No Manager section in configuration file: %s' % conf_file_fullpath)
        print('Default manager is calsource: %s' % known_hosts['calsource'])
        return known_hosts['calsource']

    return conf['manager'][0]

        
def get_myip():
    '''
    get the IP address of the local machine
    '''
    cmd = '/sbin/ip addr show up scope global'
    out,err = shellcommand(cmd)

    addr = None

    lines = out.split('\n')
    for line in lines:
        cleanline = line.strip()
        if cleanline.find('inet ')!=0: continue

        fulladdr = line.split()[1]
        addr = fulladdr.split('/')[0]

        # return preferentially with the QUBIC housekeeping network address
        if addr.find('192.168.2.')==0:
            return addr

    return addr


