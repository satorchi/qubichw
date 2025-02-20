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
import socket,time,re,os,multiprocessing,sys
import datetime as dt
from copy import deepcopy

from qubichk.utilities import shellcommand, get_myip, known_hosts, get_calsource_host

# the numato relay for switching on/off
from qubichw.relay import device_address as relay_device_address
device_list = list(relay_device_address.keys())

valid_commands = {}
for dev in device_list:
    valid_commands[dev] = ['on','off']

# the calibration source
valid_commands['calsource_150'] += ['default','frequency']
valid_commands['calsource_220'] += ['default','frequency']

# the low noise amplifier
from qubichw.amplifier_femto import default_setting as amplifier_default_setting
valid_commands['amplifier'] += ['default'] + list(amplifier_default_setting.keys())

# the redpitaya for modulating the calibration source and for reading the calsource monitor
from qubichw.redpitaya import default_setting as modulator_default_setting
valid_commands['modulator'] += ['default'] + list(modulator_default_setting.keys())

# only import hardware modules if we are on the Raspberry Pi
if os.uname().machine.find('arm')>=0:
    from qubichw.relay import relay
    from qubichw.calibration_source import calibration_source
    from qubichw.amplifier_femto import amplifier
    from qubichw.redpitaya import redpitaya as modulator


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
        h = open(filename,'a')
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

        self.device_list = device_list
        
        self.valid_commands = valid_commands

        # time it takes for a device to register with the operating system
        # the calsource, only 1 second
        # the redpitaya requires ??
        self.wait_after_switch_on = {}
        self.wait_after_switch_on['modulator'] = 5
        self.wait_after_switch_on['calsource'] = 1
        self.wait_after_switch_on['amplifier'] = 1

        self.estimated_wait = deepcopy(self.wait_after_switch_on)
        self.estimated_wait['modulator'] = 5
        
        self.device = {} # the objects instantiated for each device
        self.device_on = {} # on/off state of each device
        for dev in self.device_list:
            self.device[dev] = None
            self.device_on[dev] = None

            
        self.relay_lastcommand_date = dt.datetime.utcnow()
        self.relay_timeout = 1
        
        self.broadcast_port = 37020
        self.nbytes = 1024

        # try to get hostname from the ethernet device
        ip_addr = get_myip()
        self.hostname = ip_addr
        if ip_addr is not None and ip_addr in known_hosts.values():
            self.hostname = next(key for key,val in known_hosts.items() if val==ip_addr)

        # finally, if still undefined
        if self.hostname is None:
            self.hostname = 'localhost'

        self.receiver = ip_addr
        if role is None:
            if self.hostname=='calsource' or self.hostname=='pigps':
                role = 'manager'
            else:
                role = 'commander'
        self.role = role
                
        self.log('Calibration Source Configuration: I am %s as the %s' % (self.hostname,self.role))
        
        if self.role=='manager':
            self.log('creating hardware modules',verbosity=2)
            self.device['modulator'] = modulator()
            self.device['calsource_150'] = calibration_source('LF')
            self.device['calsource_220'] = calibration_source('HF')
            self.device['amplifier'] = amplifier()
            self.device['relay'] = relay()            

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
            
            if cmd=='default':
                command['all']['default'] = True
                for dev in ['calsource','amplifier','modulator']:
                    command[dev]['default'] = True
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
                    self.log('%s %s = %f (a number)' % (dev,parm,command[dev][parm]),verbosity=3)
                except:
                    command[dev][parm] = val
                    self.log('%s %s = %s (a string)' % (dev,parm,command[dev][parm]),verbosity=3)
                    
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
        self.log('listening on %s port %i' % (self.receiver,self.broadcast_port))

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.bind((self.receiver, self.broadcast_port))

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
        
        if timeout is None: timeout = max(self.estimated_wait.values())
        if timeout < 25: timeout = 25
        self.log('waiting up to %.0f seconds for acknowledgement from %s' % (timeout,self.receiver))
        
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(timeout)
        s.bind((self.receiver, self.broadcast_port))

        now = dt.datetime.utcnow()

        try:
            ack, addr = s.recvfrom(self.nbytes)
        except:
            self.log('no response from Calibration Source Manager')
            return None
        received_date = dt.datetime.utcnow()
        received_tstamp = eval(received_date.strftime('%s.%f'))
        self.log('acknowledgement from %s at %s' % (addr,received_date.strftime(self.date_fmt)))
        # clean up the acknowledgement
        ack_cleaned = []
        for line in ack.decode().strip().split():
            ack_cleaned.append(line.strip())
        self.log('\n'.join(ack_cleaned))
        return received_tstamp, ack
    

    def onoff(self,states=None):
        '''
        switch on or off devices
        argument: states is a dictionary with on/off state for each device
                  if states is None, get status
        '''
        reset_delta = self.relay_timeout # minimum time to wait
        now = dt.datetime.utcnow()
        delta = (now - self.relay_lastcommand_date).total_seconds()

        if delta < reset_delta:
            extra_wait = reset_delta - delta
            time.sleep(extra_wait)

        ack = ''
        if states is not None:
            info = self.device['relay'].set_state(states)
            if info['ok']:
                ack = 'OK-'
            else:
                ack = 'FAILED_SET_STATE-'
            if 'error_message' in info.keys():
                self.log('RELAY error: %s' % info['error_message'])
            self.log('RELAY message: %s' % info['message'])
            
                
        # check for the on/off status
        time.sleep(reset_delta) # wait a bit before sending another command
        states_read = self.device['relay'].state()
        if states_read is not None:
            ack += 'OK'
            self.log('retrieved RELAY states: %s' % states_read,verbosity=2)
        else:
            ack += 'FAILED_GET_STATES'
            self.log('FAILED to get RELAY states',verbosity=2)
            
        if ack.find('FAILED_GET_STATES')<0:
            self.device_on = states_read

        self.relay_lastcommand_date = dt.datetime.utcnow()
        return ack


    def status(self):
        '''
        return status of all the components
        '''
        msg = ''

        # get on/off status
        ack = self.onoff()
        for dev in self.device_list:
            if self.device_on[dev] is not None:
                if self.device_on[dev]:
                    msg += ' %s:ON' % dev
                else:
                    msg += ' %s:OFF' % dev
            else:
                msg += ' %s:UNKNOWN' % dev

        for dev in self.device_list:
            if (self.device_on[dev] is None or self.device_on[dev]) and self.device[dev].is_connected():
                msg += ' '+self.device[dev].status()
            else:
                msg += ' %s:UNKNOWN' % dev
            
        return msg
    
    def interpret_commands(self,command,retval):
        '''
        interpret the dictionary of commands, and take the necessary steps
        this method is called by the "manager"
        '''
        self.log('interpreting command: %s' % command,verbosity=2)
        ack = '%s ' % dt.datetime.utcnow().strftime('%s.%f')

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
                    state = 1
                if command[dev][parm] == 'off':
                    state = 0
                if state is not None:
                    states[dev] = state
                    msg += '%s:%s ' % (dev,command[dev][parm])
        if states:
            msg += 'relay:%s ' % self.onoff(states)
            retval['device_on'] = self.device_on
            self.log(msg)
            ack += '%s ' % msg

            # initialize devices that need initializing
            already_waited = 0
            for dev in ['modulator','calsource_150','calsource_220','amplifier']:
                if not (dev in states.keys() and states[dev] and device_was_off[dev]):
                    self.log('not doing anything for %s' % dev)
                    continue
                    
                wait_time = self.wait_after_switch_on[dev] - already_waited
                if wait_time > 0:
                    self.log('waiting %i seconds after switch on' % wait_time,verbosity=0)
                    time.sleep(wait_time)
                    already_waited += wait_time

                if not self.device[dev].is_connected():
                    self.log('%s is not connected.  re-initializing.' % dev)
                    self.device[dev].init()
                        
                            
                self.log('asking for default settings on %s' % dev)
                self.device[dev].set_default_settings()
                retval['%s state' % dev] = self.device[dev].state
                    

        # do configuration command for calsource
        parm =  'frequency'
        for dev in ['calsource_150','calsource_220']:
            if len(command[dev])==0: continue
            if 'default' in command[dev].keys() and command[dev]['default']:
                of = self.device[dev].set_default_settings()
                msg += '%s:frequency=%+06fGHz' % (dev,of)
            elif parm in command[dev].keys():
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
        if len(command[dev])>0:
            
            if 'default' in command[dev].keys() and command[dev]['default']:
                self.device[dev].set_default_settings(channel=self.modulator_channel[dev])
            else:
                for modcmd in valid_commands[dev]:
                    if modcmd not in command[dev].keys():
                        command[dev][modcmd] = None
                self.device[dev].configure(frequency=command[dev]['frequency'],
                                           amplitude=command[dev]['amplitude'],
                                           shape=command[dev]['shape'],
                                           offset=command[dev]['offset'],
                                           duty=command[dev]['duty'],
                                           output=command[dev]['output'],
                                           input_gain=command[dev]['input_gain'],
                                           acquisition_units=command[dev]['acquisition_units'],
                                           decimation=command[dev]['decimation'],
                                           coupling=command[dev]['coupling'],
                                           channel=self.modulator_channel[dev])


            # wait a bit before trying to read the results
            time.sleep(1)
            status = self.device[dev].status()
            if status is None:
                msg = '%s:FAILED' % dev
            else:
                msg = status
                
            self.log(msg)
            ack += '%s ' % msg


        # the amplifier configuration
        dev = 'amplifier'
        if len(command[dev])>0:
            if 'default' in command[dev].keys() and command[dev]['default']:
                self.device[dev].set_default_settings()
                ack += '%s:default_settings ' % dev
            else:
                for parm in command[dev].keys():
                    if parm=='onoff': continue # ignore on/off.  This is executed above.
                    ack += '%s ' % self.device[dev].set_setting(parm,command[dev][parm])
                    retval['%s state' % dev] = self.device[dev].state
        

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

            retval = {}
            retval['ACK'] = 'no acknowledgement'
            retval = self.interpret_commands(command,retval)
            cmdstr = None
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
        calsource_host = get_calsource_host()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(0.2)

        now = dt.datetime.utcnow()
        now_str = now.strftime('%s.%f')
        len_nowstr = len(now_str)
        len_remain = self.nbytes - len_nowstr - 1
        fmt = '%%%is %%%is' % (len_nowstr,len_remain)
        msg = fmt % (now_str,cmd_str)
        log_msg = ' '.join(msg.split())
        self.log('sending socket data to %s port %i: %s' % (calsource_host,self.broadcast_port,log_msg),verbosity=1)

        s.sendto(msg.encode(), (calsource_host, self.broadcast_port))
        sockname = s.getsockname()
        self.log("send_command() NOT closing socket: (%s,%i)" % sockname, verbosity=5)
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
        self.log('sending acknowledgement: %s' % msg.strip())
        try:
            s.sendto(msg.encode(), (addr, self.broadcast_port))
        except:
            self.log('Error! Could not send acknowledgement to %s:%i' % (addr,self.broadcast_port))

        sockname = s.getsockname()
        self.log("send_ack() NOT closing socket: (%s,%i)" % sockname, verbosity=5)
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

                if cmd.find('on')>=0 or cmd.find('off')>=0:
                    duration += self.energenie_timeout

                if cmd.find('on')>=0:
                    duration += max(self.estimated_wait.values())
                    

            # add margin to the acknowledgement timeout
            duration += 5
            response = self.listen_for_acknowledgement(timeout=duration)
                
        return
                
