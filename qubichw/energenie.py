'''
$Id: energenie.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 03 Nov 2022 14:14:37 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

control of the Energenie USB power bar.  Code originally was in hk_verify.py
'''
import time,re,os
import datetime as dt
from qubichk.utilities import shellcommand, ping

class energenie:
    '''
    class to turn on/off devices using the Energenie power bar
    '''
    verbosity = 2
    serial_no = {}
    serial_no['electronics rack'] = '01:01:5c:f9:d0'
    serial_no['cryostat']         = '01:01:4f:ce:8d'  # to be confirmed
    serial_no['mount']            = '01:01:4f:c4:8f'  # to be confirmed
    serial_no['calsource']        = '01:01:5f:06:f2'

    def __init__(self,name='electronics rack'):
        if 'HOSTNAME' in os.environ.keys():
            hostname = os.environ['HOSTNAME']
        else:
            hostname,err = shellcommand('hostname')

        valid_names = ['electronics rack','calsource','cryostat','mount']
        self.socket = {}
        self.ok = False
        self.name = name

        if name not in valid_names:
            self.log('invalid Energenie identifier: %s' % name)
            self.manager = None
            return        

        if name=='electronics rack':
            if not self.verify_app('which sispmctl'): return
            self.manager = self.get_manager(name,'sispmctl')
            self.socket[1] = 'horn'
            self.socket[2] = 'heaters'
            self.socket[3] = 'hwp'
            self.socket[4] = 'thermos'

        if name=='cryostat':
            if not self.verify_app('which sispmctl'): return
            self.manager = self.get_manager(name,'sispmctl')
            self.socket[1] = 'network switch'
            self.socket[2] = 'unused'
            self.socket[3] = 'Opal Kelly RaspberryPi'
            self.socket[4] = 'FPGA'

        if name=='mount':
            if not self.verify_app('which sispmctl'): return
            self.manager = self.get_manager(name,'sispmctl')
            self.socket[1] = 'motor'
            self.socket[2] = 'unused'
            self.socket[3] = 'unused'
            self.socket[4] = 'unused'
            
            
        if name=='calsource':
            if hostname.find('pigps')>=0:
                if not self.verify_app('which sispmctl'): return
                self.manager = self.get_manager(name,'sispmctl')
            else:
                pingresult = ping('pigps',verbosity=self.verbosity)
                if not pingresult['ok']:
                    msg = 'ERROR: PiGPS is UNREACHABLE'
                    self.log(msg,verbosity=1)
                    return
                if not self.verify_app('ssh pigps which sispmctl'): return
                self.manager = self.get_manager(name,'ssh pigps sispmctl')

            # make sure this is the same as in the calsource_configuration_manager
            self.socket[1] ='modulator'
            self.socket[2] ='calsource'
            self.socket[3] ='lamp'
            self.socket[4] ='amplifier'
        
        # reverse look-up
        self.devicesocket = {}
        for socknum in self.socket.keys():
            self.devicesocket[self.socket[socknum]] = socknum
    
        
        self.ok = True
        return

    def log(self,msg,verbosity=0):
        '''
        log message to screen and to a file
        '''
        if verbosity > self.verbosity: return
        
        filename = 'energenie.log'
        h = open(filename,'a')
        h.write('%s|ENERGENIE| %s\n' % (dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'),msg))
        h.close()
        print(msg)
        return


    def verify_app(self,verify_cmd):
        '''
        verify that the Energenie manager application is installed
        '''
        out,err = shellcommand(verify_cmd)
        if out=='':
            error_message = '%s application not found.' % self.manager
            msg = 'ERROR! %s\n--> Please install the application at http://sispmctl.sourceforge.net' % error_message
            self.log(msg,verbosity=1)
            return False
        return True
                
    
    def get_manager(self,pbname,manager):
        '''
        get the manager command (including the device index) of the required Energenie powerbar
        '''

        if pbname not in self.serial_no.keys():
            self.log('ERROR! unknown Energenie power bar: %s' % pbname,verbosity=1)
            return None
        
        cmd = '%s -s' % manager
        out,err = shellcommand(cmd) # scan for Energenie devices

        device_index = {}        
        idx = 0
        for line in out.split('\n'):
            if line.find('serial number')==0:
                snum = line.replace('serial number:','').strip()
                device_index[snum] = idx
                idx += 1

        
        snum = self.serial_no[pbname]
        if snum not in device_index.keys():
            self.log('ERROR! Energenie power bar not connected: %s with serial number %s' % (pbname,snum))
            return None
        
        dev_idx = device_index[snum]
        manager_cmd = '%s -d%i' % (manager,dev_idx)
        return manager_cmd

    def get_socket_states(self):
        '''
        get the socket states of the Energenie powerbar
        '''
        states = {}
        states['ok'] = True
        states['error_message'] = None

        cmd = '%s -g all' % self.manager
        
        # try a few times to connect to the Energenie USB powerbar
        error_counter = 0
        max_count = 3
        match = None
        find_str = '(Status of outlet [1-4]:\t)(off|on)'
        while match is None and error_counter<max_count:
            out,err = shellcommand(cmd)
            match = re.search(find_str,out)
            if match is None:
                error_counter += 1
                states['error_message'] = 'USB Energenie powerbar not detected: error count=%i' % error_counter
                if err: states['error_message'] += '\n'+err
                if out: states['error_message'] += '\n'+out
                self.log(msg,verbosity=1)
                if error_counter<max_count: time.sleep(3)

        if match is None:
            states['ok'] = False
            msg = 'ERROR! %s\n-->Please check USB connection' % retval['error_message']
            self.log(msg,verbosity=1)
            return states
   

        for socknum in self.socket.keys():
            find_str = '(Status of outlet %i:\t)(off|on)' % socknum
            match = re.search(find_str,out)
            if match is None:
                states['ok'] = False
                msg = 'Could not find Energenie power status for %s' % self.socket[socknum]
                states['error_message'] = msg
                self.log(msg,verbosity=1)
                status_str = 'UNKNOWN'
                states[socknum] = status_str
            else:
                status_str = match.groups()[1]
                if status_str == 'on':
                    status = True
                else:
                    status = False
            
            states[socknum] = status
            
        return states


    def set_socket_states(self,states):
        '''
        set the socket states of the calibration source Energenie powerbar (RCPB1)
        '''

        retval = {}
        retval['ok'] = True
        errmsg_list = []
        msg_list = []
        on_cmd = '-o'
        off_cmd = '-f'
        for socket in states.keys():
            if states[socket]:
                cmd = '%s %s %i' % (self.manager,on_cmd,socket)
            else:
                cmd = '%s %s %i' % (self.manager,off_cmd,socket)
            self.log('setting energenie socket state with command: %s' % cmd,verbosity=1)
            out,err = shellcommand(cmd)
            msg_list.append(out.strip())
            if err: errmsg_list.append(err.strip())

        retval['message'] = '\n'.join(msg_list)
        if len(errmsg_list)>0:
            retval['ok'] = False
            retval['error_message'] = '\n'.join(errmsg_list)
        
        return retval

    def switch_onoff(self,devname,onoff):
        '''
        switch on a particular device
        '''
        retval = {}
        retval['message'] = ''
        retval['error_message'] = ''
        retval['ok'] = False
        
        if onoff.lower()=='on':
            onoff_cmd = '-o'
        else:
            onoff_cmd = '-f'
        
        if devname not in self.devicesocket.keys():
            retval['error_message'] = 'unknown device: %s' % devname
            self.log(retval['error_message'],verbosity=1)
            return retval

        cmd = '%s %s %i' % (self.manager,onoff_cmd,self.devicesocket[devname])
        out,err = shellcommand(cmd)
        if err:
            retval['error_message'] = err.strip()
            self.log(retval['error_message'),verbosity=1)
            return retval
        retval['ok'] =  True
        return retval

    def switchon(self,devname):
        '''
        wrapper to switch on the given device
        '''
        return self.switch_onoff(devname,'on')

    def switchoff(self,devname):
        '''
        wrapper to switch off the given device
        '''
        return self.switch_ononff(devname,'off')
    
    
    def get_status(self,verbosity=1,modulator_state=False):
        '''
        check for the status of the Energenie sockets
        '''
        retval = {}
        retval['ok'] = True
        retval['error_message'] = ''
        retval['message'] = ''
        errmsg_list = []
        msg_list = []

        error_counter = 0
        max_count = 3
        states = None
        while (states is None and error_counter<max_count):
            msg = 'checking for %s Energenie socket states' % self.name
            self.log(msg,verbosity=1)
            time.sleep(3)
            states = self.get_socket_states()
            if states is not None:
                for socknum in self.socket.keys():
                    dev = self.socket[socknum]
                    if socknum not in states.keys():
                        msg = '%s is UNKNOWN' % dev
                    elif states[socknum]:
                        msg = '%s is ON' % dev
                    else:
                        msg = '%s is OFF' % dev
                    self.log(msg,verbosity=1)
                    msg_list.append(msg)

            else:
                error_counter += 1
                states = None
                msg = 'Could not get socket states from %s Energenie powerbar: error count=%i' % (self.name,error_counter)
                self.log(msg,verbosity=1)
                msg_list.append(msg)
                errmsg_list.append(msg)

        retval['states'] = states
        if states is None: retval['ok'] = False

            
        if len(errmsg_list)>0: retval['error_message'] += '\n  '.join(errmsg_list)    
        retval['message'] = '\n'.join(msg_list)
        return retval
