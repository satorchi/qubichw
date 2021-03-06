'''
$Id: calsource_configuration_manager.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Fri 08 Feb 2019 08:25:47 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

A class with methods to send/receive configuration command for the calibration source setup
Commands are sent to switch on/off and configure three components: calsource, amplifier, modulator
'''
from __future__ import division, print_function
import socket,subprocess,time,re,os,multiprocessing,sys
import datetime as dt

# the Energenie powerbar
#from PyMS import PMSDevice
from qubichk.hk_verify import energenie_cal_set_socket_states as energenie_set_socket_states
from qubichk.hk_verify import energenie_cal_get_socket_states as energenie_get_socket_states

# the calibration source
from qubichw.calibration_source import calibration_source

# the low noise amplifier
from qubichw.amplifier import amplifier

# the signal generator for modulating the calibration source
#from qubichw.modulator import modulator
from qubichw.modulator_tg5012a import tg5012 as modulator

# the Arduino Uno
from qubichw.arduino import arduino

from satorchipy.datefunctions import tot_seconds

class calsource_configuration_manager():

    def __init__(self,role=None, verbosity=0):
        '''
        initialize the object.  The role can be either "commander" or "manager"
        The "manager" runs on the Raspberry Pi, and interfaces directly with the hardware
        The "commander" sends commands via socket to the "manager"
        '''
        self.verbosity = verbosity
        self.assign_variables(role)
        if self.role == 'manager':
            self.listen_loop()
        elif self.role == 'bot':
            pass # create object but don't go into the Command Line Interface loop.
        else:
            self.command_loop()
            
        return None

    def log(self,msg,verbosity=0):
        '''
        log message to screen and to a file
        '''
        if verbosity > self.verbosity: return
        
        filename = 'calsource_configuration_%s.log' % self.role
        h=open(filename,'a')
        h.write('%s: %s\n' % (dt.datetime.utcnow().strftime(self.date_fmt),msg))
        h.close()
        print(msg)
        return

    def command_help(self):
        '''
        print some help text to screen
        '''
        device_list_str = ', '.join(self.device_list)
        txt  = 'Calibration Source Commander:  Help\n'
        txt += 'commands should be given in the following format:\n'
        txt += '    <device>:<parameter>[=<value>]\n\n'
        txt += 'except for the following commands which are independent of device: help, status, on, off, save\n\n'
        txt += 'valid devices: %s\n' % device_list_str
        for dev in self.device_list:
            valid_commands = ', '.join(self.valid_commands[dev])
            txt += 'valid commands for %s: %s\n' % (dev,valid_commands)
        txt += '\nFor the modulator, frequency is given in Hz\n'
        txt += 'For the calibration source, frequency is given in GHz\n'
        txt += '\nFor the arduino, duration is given in seconds.\n'
        txt += 'Note that this command will immediately start an acquisition.\n'
        txt += '\nExample:\n'
        txt += 'calsource:on amplifier:on modulator:on modulator:frequency=0.333 modulator:duty=33 modulator:shape=squ calsource:frequency=150\n'
        print(txt)
        return
    
    def assign_variables(self,role):
        '''
        initialize variables, depending on the role
        if the role is "manager", we need to connect to the hardware
        '''
        self.role = role

        self.date_fmt = '%Y-%m-%d %H:%M:%S.%f'
        # the device list is in the order that they are plugged into the Energenie powerbar
        self.device_list = ['modulator','calsource','lamp','amplifier','arduino']

        self.valid_commands = {}
        self.valid_commands['modulator'] = ['on','off','frequency','amplitude','offset','duty','shape']
        self.valid_commands['calsource'] = ['on','off','frequency']
        self.valid_commands['amplifier'] = ['on','off',
                                            'filter_mode',
                                            'dynamic_range',
                                            'gain',
                                            'filter_low_frequency',
                                            'filter_high_frequency',
                                            'coupling',
                                            'invert']
        self.valid_commands['lamp' ]     = ['on','off']
        self.valid_commands['arduino']   = ['duration']
        
        self.device = {}
        self.powersocket = {}
        self.device_on = {}
        for idx,dev in enumerate(self.device_list):
            self.powersocket[dev] = idx + 1
            self.device[dev] = None
            self.device_on[dev] = None
            
        self.energenie_lastcommand_date = dt.datetime.utcnow()
        self.energenie_timeout = 5

        self.known_hosts = {}
        self.known_hosts['qubic-central'] = "192.168.2.1"
        self.known_hosts['qubic-studio']  = "192.168.2.8"
        self.known_hosts['calsource']     = "192.168.2.5"
        self.known_hosts['pigps'] = '192.168.2.17'
        
        self.broadcast_port = 37020
        self.nbytes = 1024
        self.receiver = self.known_hosts['pigps']

        self.energenie = None
        self.hostname = None
        if self.hostname is None and 'HOST' in os.environ.keys():
            self.hostname = os.environ['HOST']
            
        # try to get hostname from the ethernet device
        cmd = '/sbin/ifconfig -a'
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = proc.communicate()
        match = re.match('.* inet (192\.168\.2\..*?) ',out.decode().replace('\n',' '))
        if match:
            ip_addr = match.groups()[0]
            if ip_addr in self.known_hosts.values():
                self.hostname = next(key for key,val in self.known_hosts.items() if val==ip_addr)
            else:
                self.hostname = ip_addr

        # finally, if still undefined
        if self.hostname is None:
            self.hostname = 'localhost'

        if role is None:
            if self.hostname=='calsource' or self.hostname=='pigps':
                role = 'manager'
            else:
                role = 'commander'
        self.role = role
                
        if role=='manager':
            self.log('I am the calsource configuration manager')
            #self.energenie = PMSDevice('energenie', '1')
            self.device['modulator'] = modulator()
            self.device['calsource'] = calibration_source('LF')
            self.device['arduino']   = arduino()
            self.device['amplifier'] = amplifier()

        self.log('Calibration Source Configuration: I am %s as the %s' % (self.hostname,self.role))
        return None

    def parse_command_string(self,cmdstr):
        '''
        parse the command string into a command dictionary
        '''

        # the returned command dictionary is a dictionary of dictionaries
        command = {}
        command['timestamp'] = {}
        for dev in self.device_list:
            command[dev] = {}

        command['all'] = {}
        command['all']['status'] = False
        
        command_lst = cmdstr.strip().lower().split()
        tstamp_str = command_lst[0]
        try: # in case the commander forgot to send the timestamp before the command
            command['timestamp']['sent'] = eval(tstamp_str)
            command_lst = command_lst[1:]
        except:
            command['timestamp']['sent'] = 0.0
        
        dev = 'unknown'
        for cmd in command_lst:
            if cmd=='status':
                command['all']['status'] = True
                continue

            if cmd=='on' or cmd=='off':
                command['all']['onoff'] = cmd
                for dev in ['calsource','amplifier','modulator']:
                    command[dev]['onoff'] = cmd
                continue

            if cmd=='save':
                command['arduino']['save'] = True
                continue
                    
            
            cmd_lst = cmd.split(':')
            try:
                devcmd = cmd_lst[1]
                dev = cmd_lst[0]
            except:
                # if we forget to specify the device, use the most recent one
                devcmd = cmd_lst[0]

            if dev not in self.device_list:
                continue
            
            if devcmd.find('=')>0:
                devcmd_lst = devcmd.split('=')
                parm = devcmd_lst[0]
                val = devcmd_lst[1]

                if parm not in self.valid_commands[dev]:
                    continue
                
                try:
                    command[dev][parm] = eval(val)
                    self.log('%s %s = %f (a number)' % (dev,parm,command[dev][parm]),verbosity=2)
                except:
                    command[dev][parm] = val
                    self.log('%s %s = %s (a string)' % (dev,parm,command[dev][parm]),verbosity=2)
                    
            else:
                if devcmd=='on' or devcmd=='off':
                    parm = 'onoff'
                    val = devcmd
                    if devcmd not in self.valid_commands[dev]:
                        continue
                else:
                    parm = devcmd
                    val = True
                    if parm not in self.valid_commands[dev]:
                        continue
                command[dev][parm] = val
        return command


    def listen_for_command(self):
        '''
        listen for a command string arriving on socket
        this message is called by the "manager"
        '''
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.bind((self.receiver, self.broadcast_port))

        self.log('listening on %s' % self.receiver)

        now = dt.datetime.utcnow()        
        try:
            cmdstr, addr_tple = s.recvfrom(self.nbytes)
            addr = addr_tple[0]
            cmdstr_clean = ' '.join(cmdstr.decode().strip().split())
        except socket.error:
            addr = 'NONE'
            cmdstr_clean = '%s SOCKET ERROR' % now.strftime('%s.%f')

        except:
            addr = 'NONE'
            cmdstr_clean = '%s UNKNOWN ERROR' %  now.strftime('%s.%f')
            
        
        received_date = dt.datetime.utcnow()
        received_tstamp = eval(received_date.strftime('%s.%f'))
        self.log('received a command from %s at %s: %s' % (addr,received_date.strftime(self.date_fmt),cmdstr_clean))
        return received_tstamp, cmdstr_clean, addr

    def listen_for_acknowledgement(self,timeout=None):
        '''
        listen for an acknowledgement string arriving on socket
        this message is called by the "commander" after sending a command
        '''
        if timeout is None: timeout = 25
        if timeout < 25: timeout = 25
        
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(timeout)
        s.bind((self.hostname, self.broadcast_port))

        now = dt.datetime.utcnow()
        self.log('waiting up to %.0f seconds for acknowledgement on %s' % (timeout,self.hostname))

        try:
            ack, addr = s.recvfrom(self.nbytes)
        except:
            self.log('no response from Calibration Source Manager')
            return None
        received_date = dt.datetime.utcnow()
        received_tstamp = eval(received_date.strftime('%s.%f'))
        self.log('acknowledgement from %s at %s' % (addr,received_date.strftime(self.date_fmt)))
        # clean up the acknowledgement
        ack_cleaned = ''
        for line in ack.decode().strip().split('|'):
            ack_cleaned += '%s\n' % line.strip()
        self.log(ack_cleaned)
        return received_tstamp, ack
    

    def onoff(self,states=None):
        '''
        switch on or off devices
        we have to wait for the Energenie powerbar to reset
        '''
        reset_delta = self.energenie_timeout # minimum time to wait
        now = dt.datetime.utcnow()
        delta = tot_seconds(now - self.energenie_lastcommand_date)

        if delta < reset_delta:
            extra_wait = reset_delta - delta
            time.sleep(extra_wait)

        ack = ''
        if states is not None:
            info = energenie_set_socket_states(states)
            if info['ok']:
                ack = 'OK-'
            else:
                ack = 'FAILED_SET_STATES-'
            if 'error_message' in info.keys():
                self.log('energenie error: %s' % info['error_message'])
            self.log('energenie message: %s' % info['message'])
            
                
        # check for the on/off status
        time.sleep(reset_delta) # wait a bit before sending another command
        states_read = energenie_get_socket_states()
        if states_read is not None:
            ack += 'OK'
            self.log('retrieved energenie states: %s' % states_read,verbosity=2)
        else:
            ack += 'FAILED_GET_STATES'
            self.log('FAILED to get energenie states',verbosity=2)
            
        if ack.find('FAILED_GET_STATES')<0:
            for socket_no in states_read.keys():
                socket_idx = socket_no - 1
                state = states_read[socket_no]
                dev = self.device_list[socket_idx]
                self.device_on[dev] = state

        self.energenie_lastcommand_date = dt.datetime.utcnow()
        return ack


    def status(self):
        '''
        return status of all the components
        '''
        msg = ''

        # get on/off status from Energenie powerbar
        ack = self.onoff()
        for dev in self.device_list:
            if self.device_on[dev] is not None:
                if self.device_on[dev]:
                    msg += ' %s:ON' % dev
                else:
                    msg += ' %s:OFF' % dev
            else:
                msg += ' %s:UNKNOWN' % dev

        dev = 'amplifier'
        if (self.device_on[dev] is None or self.device_on[dev]) and self.device[dev].is_connected():
            msg += ' '+self.device[dev].status()
            
        dev = 'calsource'
        if self.device_on[dev]:
            if self.device[dev].state is not None:
                msg += ' %s:frequency=%+06fGHz' % (dev,self.device[dev].state['frequency'])
                msg += ' synthesiser:frequency=%+06fGHz' % self.device[dev].state['synthesiser_frequency']
            else:
                msg += ' %s:frequency=UNKNOWN' % dev
                msg += ' synthesiser:frequency=UNKNOWN'
            
        dev = 'modulator'
        if self.device[dev].is_connected():
            settings = self.device[dev].read_settings(show=False)
            if settings is None:
                msg += ' %s:UNKNOWN' % dev
            else:
                '''
                # for the HP3312A
                msg += '| %s: SHAPE=%s FREQUENCY=%.6f Hz AMPLITUDE=%.6f V OFFSET=%.6f V DUTY CYCLE=%.1f%%' % \
                    (dev,
                     settings['shape'],
                     settings['frequency'],
                     settings['amplitude'],
                     settings['offset'],
                     settings['duty'])
                '''
                msg += ' %s:SHAPE=%s %s:FREQUENCY=%s %s:AMPLITUDE=%s %s:OFFSET=%s %s:DUTY_CYCLE=%s' % \
                    (dev,settings['shape'],
                     dev,settings['frequency'],
                     dev,settings['amplitude'],
                     dev,settings['offset'],
                     dev,settings['duty'])

            
        return msg
    
    def interpret_commands(self,command,retval):
        '''
        interpret the dictionary of commands, and take the necessary steps
        this method is called by the "manager"
        '''
        ack = '%s ' % dt.datetime.utcnow().strftime('%s.%f')

        # add None to modulator parameters that are to be set by default
        modulator_configure = False
        for parm in ['frequency','amplitude','shape','offset','duty']:
            if parm in command['modulator'].keys():
                modulator_configure = True
            else:
                command['modulator'][parm] = None
                
        # get current on/off status from Energenie powerbar
        onoff_ack = self.onoff()
        device_was_off = {}
        for dev in self.device_on.keys():
            device_was_off[dev] = not self.device_on[dev]

        # do all on/off commands first
        parm = 'onoff'
        states = {}
        msg = ''
        devlist = list(command.keys())
        devlist.remove('all')
        devlist.remove('timestamp')
        for dev in devlist:
            if parm in command[dev].keys():
                state = None
                if command[dev][parm] == 'on':
                    state = True
                if command[dev][parm] == 'off':
                    state = False
                if state is not None:
                    states[self.powersocket[dev]] = state
                    msg += '%s:%s ' % (dev,command[dev][parm])
        if states:
            msg += 'energenie:%s ' % self.onoff(states)
            retval['device_on'] = self.device_on
            self.log(msg)
            ack += '%s ' % msg
            # wait before doing other stuff
            wait_after_switch_on = 1
            self.log('waiting %i seconds after switch on/off' % wait_after_switch_on,verbosity=2)
            time.sleep(wait_after_switch_on)

            # initialize devices that need initializing
            for dev in ['modulator','calsource','amplifier']:
                powersocket = self.powersocket[dev]
                if powersocket in states.keys() and states[powersocket] and device_was_off[dev]:
                    self.log('asking for default settings on %s' % dev)
                    self.device[dev].set_default_settings()
                    retval['%s state' % dev] = self.device[dev].state
                else:
                    self.log('not doing anything for %s' % dev)

        # do configuration command for calsource
        dev = 'calsource'
        parm =  'frequency'
        if dev in command.keys() and parm in command[dev].keys():
            of = self.device[dev].set_Frequency(command[dev][parm])
            msg = '%s:%s=%+06fGHz ' % (dev,parm,command[dev][parm])
            if of is None:
                msg += 'FAILED'
                retval['%s state' % dev] = None
            else:
                msg += 'synthesiser:frequency=%+06fGHz' % of
                retval['%s state' % dev] = self.device[dev].state
            self.log(msg)
            ack += '%s ' % msg
                

        # the modulator configuration
        dev = 'modulator'
        if dev in command.keys() and modulator_configure:
            self.device[dev].configure(frequency=command[dev]['frequency'],
                                       amplitude=command[dev]['amplitude'],
                                       shape=command[dev]['shape'],
                                       offset=command[dev]['offset'],
                                       duty=command[dev]['duty'])

            # wait a bit before trying to read the results
            time.sleep(1)
            settings = self.device[dev].read_settings(show=False)
            if settings is None:
                msg = '%s:FAILED' % dev
            else:
                msg = '%s:SHAPE=%s %s:FREQUENCY=%s %s:AMPLITUDE=%s %s:OFFSET=%s %s:DUTY_CYCLE=%s' % \
                    (dev,settings['shape'],
                     dev,settings['frequency'],
                     dev,settings['amplitude'],
                     dev,settings['offset'],
                     dev,settings['duty'])
                    
            self.log(msg)
            ack += '%s ' % msg


        # the amplifier configuration
        dev = 'amplifier'
        if dev in command.keys():
            for parm in command[dev].keys():
                if parm!='onoff': # ignore on/off.  This is executed above.
                    ack += '%s ' % self.device[dev].set_setting(parm,command[dev][parm])
                    retval['%s state' % dev] = self.device[dev].state
        
        # run the Arduino last of all
        dev = 'arduino'
        if dev in command.keys():
            if 'duration' in command[dev].keys():
                filename = self.device[dev].acquire(command[dev]['duration'])
                if filename is None:
                    ack += '%s:acquisition=failed ' % dev
                else:
                    ack += '%s:file=%s ' % (dev,filename)

            if 'save' in command[dev].keys():
                self.device[dev].interrupt()

        # STATUS
        if command['all']['status']:
            ack += '%s ' % self.status()
            

        retval['ACK'] = ack.strip()
        return retval


    def listen_loop(self):
        '''
        keep listening on the socket for commands
        '''
        cmdstr = None
        keepgoing = True
        while keepgoing:
            if cmdstr is None: received_tstamp, cmdstr, addr = self.listen_for_command()
            command = self.parse_command_string(cmdstr)
            try:
                sent_date = dt.datetime.fromtimestamp(command['timestamp']['sent'])
                self.log('command sent:     %s' % sent_date.strftime(self.date_fmt))
            except:
                self.log('command sent:     %s' % command['timestamp']['sent'])
                         
            received_date = dt.datetime.fromtimestamp(received_tstamp)
            self.log('command received: %s' % received_date.strftime(self.date_fmt))

            # interpret the commands in a separate process and continue listening
            manager = multiprocessing.Manager()
            retval = manager.dict()
            retval['ACK'] = 'no acknowledgement'
            proc = multiprocessing.Process(target=self.interpret_commands, args=(command,retval))
            proc.start()
            if 'arduino' in command.keys() and 'duration' in command['arduino'].keys():
                delta = dt.timedelta(seconds=command['arduino']['duration'])
                now = dt.datetime.utcnow()
                stoptime = now + delta
                self.send_acknowledgement('Send command "save" to interrupt and save immediately',addr)
                working = True
                self.log("going into loop until %s or until 'save' command received" % stoptime.strftime('%Y-%m-%d %H:%M:%S UT'))
                while working and now<stoptime:
                    received_tstamp, cmdstr, addr = self.listen_for_command()
                    now = dt.datetime.utcnow()
                    command2 = self.parse_command_string(cmdstr)
                    if 'arduino' in command2.keys() and 'save' in command2['arduino'].keys():
                        self.device['arduino'].interrupt()
                        working = False
                        cmdstr = None
                    elif now<stoptime:
                        self.send_acknowledgement("I'm busy and can only respond to the 'save' command",addr)
                    else:
                        self.log('command will be carried into main loop: %s' % cmdstr)
            else:
                cmdstr = None

            proc.join()
            if len(retval)==0:
                ack = 'no acknowledgement'
            else:
                ack = retval['ACK']
            if 'device_on' in retval.keys():
                self.device_on = retval['device_on']
            if 'calsource state' in retval.keys():
                self.device['calsource'].state = retval['calsource state']
            if 'amplifier state' in retval.keys():
                # reassign amplifier state in the amplifier object
                # this is a weirdness I don't quite understand because of using multiprocess
                # does it make a temporary copy of the amplifier object?
                self.device['amplifier'].state = retval['amplifier state']

            self.send_acknowledgement(ack,addr)

        return
                
    def send_command(self,cmd_str):
        '''
        send commands to the calibration source manager
        '''
        s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(0.2)

        now=dt.datetime.utcnow()
        now_str = now.strftime('%s.%f')
        len_nowstr = len(now_str)
        len_remain = self.nbytes - len_nowstr - 1
        fmt = '%%%is %%%is' % (len_nowstr,len_remain)
        msg = fmt % (now_str,cmd_str)
        #self.log('sending socket data: %s' % msg)

        s.sendto(msg.encode(), (self.receiver, self.broadcast_port))
        sockname = s.getsockname()
        self.log("send_command() NOT closing socket: (%s,%i)" % sockname, verbosity=3)
        #s.close()
        return

    def send_acknowledgement(self,ack,addr):
        '''
        send an acknowledgement to the commander
        '''
        s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(0.2)

        now=dt.datetime.utcnow()
        now_str = now.strftime('%s.%f')
        len_nowstr = len(now_str)
        len_ack = len(ack)
        len_remain = self.nbytes - len_nowstr - 1
        buf = ''
        for n in range(len_remain): buf+=' '
        msg = '%s %s%s' % (now_str,ack,buf)
        self.log('sending acknowledgement: %s' % msg)
        try:
            s.sendto(msg.encode(), (addr, self.broadcast_port))
        except:
            self.log('Error! Could not send acknowledgement to %s:%i' % (addr,self.broadcast_port))

        sockname = s.getsockname()
        self.log("send_ack() NOT closing socket: (%s,%i)" % sockname, verbosity=1)
        #s.close()
        return
    
    def command_loop(self):
        '''
        command line interface to send commands
        '''
        pythonmajor = sys.version_info[0]
        keepgoing = True
        prompt = 'Enter command ("help" for list): '
        while keepgoing:
            if pythonmajor==2:
                ans = raw_input(prompt)
            else:
                ans = input(prompt)
            cmd_str = ans.strip().lower()
            cmd_list = cmd_str.split()
            if 'help' in cmd_list or 'h' in cmd_list:
                self.command_help()
                continue

            if 'quit' in cmd_list or 'q' in cmd_list:
                keepgoing = False
                continue

            self.send_command(cmd_str)

            # check if we're doing an acquisition or other things that require extra time
            duration = 0
            for cmd in cmd_list:
                if cmd.find('arduino:duration=')==0:
                    duration_str = cmd.split('=')[1]
                    try:
                        duration += eval(duration_str)
                    except:
                        self.log('Could not interpret Arduino duration')
                    continue

                if cmd.find('on')>0 or cmd.find('off')>0:
                    duration += self.energenie_timeout
                    

            # add margin to the acknowledgement timeout
            duration += 5
            response = self.listen_for_acknowledgement(timeout=duration)
                
        return
                
