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

    def __init__(self,name='electronics rack'):
        if 'HOSTNAME' in os.environ.keys():
            hostname = os.environ['HOSTNAME']
        else:
            hostname,err = shellcommand('hostname')

        valid_names = ['electronics rack','calsource','cryostat','rack 1','rack 2']
        self.socket = {}
        self.ok = False

        if name not in valid_names:
            self.log('invalid Energenie identifier: %s' % name)
            self.manager = None
            return
        

        if name=='electronics rack' or name=='rack 1':
            verify_cmd = 'which sispmctl' 
            self.manager = 'sispmctl -d 0'
            self.socket[1] = 'horn'
            self.socket[2] = 'heaters'
            self.socket[3] = 'hwp'
            self.socket[4] = 'thermos'

        if name=='cryostat' or name=='rack 2':
            verify_cmd = 'which sispmctl' 
            self.manager = 'sispmctl -d 1'
            self.socket[1] = 'network switch'
            self.socket[2] = 'unused'
            self.socket[3] = 'Opal Kelly RaspberryPi'
            self.socket[4] = 'FPGA'
            
        if name=='calsource':
            if hostname.find('pigps')>=0:
                verify_cmd = 'which sispmctl'
                self.manager = 'sispmctl -d 0'
            else:
                pingresult = ping('pigps',verbosity=self.verbosity)
                if not pingresult['ok']:
                    msg = 'ERROR: PiGPS is UNREACHABLE'
                    self.log(msg,verbosity=1)
                    return
                verify_cmd = 'ssh pigps which sispmctl' 
                self.manager = 'ssh pigps sispmctl'


            # make sure this is the same as in the calsource_configuration_manager
            self.socket[1] ='modulator'
            self.socket[2] ='calsource'
            self.socket[3] ='lamp'
            self.socket[4] ='amplifier'


        # reverse look-up
        self.devicesocket = {}
        for socknum in self.socket.keys():
            self.devicesocket[self.socket[socknum]] = socknum
    
        # check that the Energenie manager application is installed
        out,err = shellcommand(verify_cmd)
        if out=='':
            error_message = '%s application not found.' % self.manager
            msg = 'ERROR! %s\n--> Please install the application at http://sispmctl.sourceforge.net' % error_message
            self.log(msg,verbosity=1)
            return
        
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

    
    def get_status(self,verbosity=1,modulator_state=False):
        '''
        check for the status of the calsource Energenie sockets
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
            msg = 'checking for calsource Energenie socket states'
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
                msg = 'Could not get socket states from calsource Energenie powerbar: error count=%i' % error_counter
                self.log(msg,verbosity=1)
                msg_list.append(msg)
                errmsg_list.append(msg)

        retval['states'] = states
        if states is None: retval['ok'] = False

            
        if len(errmsg_list)>0: retval['error_message'] += '\n  '.join(errmsg_list)    
        retval['message'] = '\n'.join(msg_list)
        return retval
