'''
$Id: heater.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 26 Feb 2025 14:00:50 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

heater modes to effectively create slow, mid, and high heater modes by changing the duty cycle
'''
import os,sys,socket
import datetime as dt

# the numato relay for switching on/off
from qubichw.relay import relay as numato_relay
from qubichk.utilities import get_myip

class heater():
    '''
    class to operate the heater in different heating modes
    '''
    
    PORT = 41337
    LISTENER = get_myip()
    timeout = 0.1
    nbytes = 256

    defined_mode = {}
    defined_mode['off'] = {'duty': 0,
                           'on_duration': 0
                           }
    defined_mode['slow'] = {'duty': 0.1,
                            'on_duration': 1
                            }
    defined_mode['mid'] = {'duty': 0.5,
                           'on_duration': 2
                           }
    defined_mode['fast'] = {'duty': 0.8,
                            'on_duration': 4
                            }
    defined_mode['full'] = {'duty': 1,
                            'on_duration': 1
                            }


    def __init__(self,verbosity=0):
        '''
        create the heater object
        '''
        self.verbosity_threshold = verbosity
        self.relay = numato_relay()
        
        return
    
    def log(self,msg,verbosity=0):
        '''
        print to screen if sufficiently verbose
        '''
        if verbosity>self.verbosity_threshold: return
        date_fmt = '%Y-%m-%d %H:%M:%S.%f'
        now = dt.datetime.utcnow()
        full_msg = '%s|HEATER| %s' % (dt.datetime.utcnow().strftime(date_fmt),msg)
        print(full_msg)
        return

    def init_socket(self):
        '''
        initialize the socket for listening for commands
        '''
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(self.timeout)
        s.bind((self.LISTENER, self.PORT))
        return s        

    def heateron(self):
        '''
        switch on the heater
        '''
        self.log('switching on the heater',verbosity=1)
        self.relay.switchon('heater')
        return

    def heateroff(self):
        '''
        switch off the heater
        '''
        self.log('switching off the heater',verbosity=1)
        self.relay.switchoff('heater')
        return

    def is_heateron(self):
        '''
        get the current on/off status of the heater
        '''
        relay_state = self.relay.state()
        onoff = relay_state['heater']
        return bool(onoff)
    

    def check_for_command(self,s=None):
        '''
        listen for an acknowledgement string arriving on socket
        this message is called by the "commander" after sending a command
        '''
        if s is None:
            self.log('Error! socket is not initialized')
            return None
        
        now = dt.datetime.utcnow()

        try:
            msgbytes, addr_tple = s.recvfrom(self.nbytes)
        # except socket.timeout:
        #     self.log('no message',verbosity=3)
        #     return None
        except:
            self.log('nothing on socket',verbosity=3)
            return None
    
        received_date = dt.datetime.utcnow()
        received_tstamp = received_date.timestamp()
        logmsg = '%s received command from %s: %s' % (received_date.strftime('%Y-%m-%d %H:%M:%S'),
                                                      addr_tple[0],
                                                      msgbytes.decode()
                                                      )
        self.log(logmsg,verbosity=1)

        return self.interpret_command(received_tstamp, msgbytes)

    def interpret_command(self,tstamp, cmdbytes):
        '''
        interpret the command string received on socket
        '''

        cmd_str = cmdbytes.decode()
        cmd_list = cmd_str.split()

        commandments = {}

        for command in cmd_list:
            if command.find('=')>0:
                parm_cmd_list = command.split('=')
                parm = parm_cmd_list[0]
                val_str = parm_cmd_list[1]
                try:
                    val = eval(val_str)
                except:
                    val = val_str

                commandments[parm] = val
                continue
    
            commandments[command] = 'execute'    
    
        return commandments

    def run_command(self,commandments):
        '''
        run the given command: on, off, set heater mode
        return False if we want to exit the operation loop
        '''
        cmd_result = {}
        cmd_result['keepgoing'] = True

        for cmd in commandments.keys():
            if cmd=='off':
                self.heateroff()
                cmd_result['mode'] = 'off'
                return cmd_result

            if cmd=='quit':
                self.heateroff()
                cmd_result['mode'] = 'off'
                cmd_result['keepgoing'] = False
                return cmd_result

            if cmd=='on' or cmd=='full':
                self.heateron()
                cmd_result['mode'] = 'full'
                continue

            if cmd in self.defined_mode.keys():
                cmd_result['mode'] = cmd
                cmd_result['duty'] = self.defined_mode[cmd]['duty']
                cmd_result['on_duration'] = self.defined_mode[cmd]['on_duration']
                continue

            if cmd in ['duty','on_duration']:
                cmd_result[cmd] = commandments[cmd]
                cmd_result['mode'] = 'other'
                continue

            cmd_result[cmd] = 'unknown command'

        return cmd_result

    def operation_loop(self,verbosity=0):
        '''
        run a state machine to implement the heater modes
        '''
        self.verbosity_threshold = verbosity

        sock = self.init_socket()
        if sock is None:
            self.log('Error! could not initialize socket',verbosity=0)
            return None
        
        keepgoing = True
        current_mode = 'off'
        new_mode = None
        last_statechange = dt.datetime.utcnow()
        duty = 0.0
        on_duration = 0.0
        off_duration = 1.0e6
    
        while keepgoing:
            try:
                cmd = self.check_for_command(sock)
            except KeyboardInterrupt:
                print('loop exit with ctrl-c')
                sock.close()
                return

            if cmd is not None:        
                cmd_result = self.run_command(cmd)
                keepgoing = cmd_result['keepgoing']
                if 'mode' in cmd_result.keys(): new_mode = cmd_result['mode']
            
            if not keepgoing:
                self.heateroff()
                sock.close()
                return

            if new_mode=='off':
                self.heateroff()
                current_mode='off'
                new_mode = None
                continue

            if new_mode=='full':
                self.heateron()
                current_mode='full'
                new_mode = None
                continue
        
            if new_mode is not None:
                current_mode = new_mode
                duty = cmd_result['duty']
                on_duration = cmd_result['on_duration']
                off_duration = on_duration/duty
                new_mode = None

            if current_mode=='off':
                # check that the heater is really off
                if self.is_heateron(): self.heateroff()
                continue
        
            if current_mode=='full':
                # check that the heater is really on
                if not self.is_heateron(): self.heateron()
                continue

            now = dt.datetime.utcnow()
            delta = now - last_statechange
            delta_seconds = delta.total_seconds()
            if self.is_heateron():
                if delta_seconds >= on_duration:
                    self.heateroff()
                    last_statechange = now
                    continue
                continue
            else:
                if delta_seconds >= off_duration:
                    self.heateron()
                    last_statechange = now
                    continue
                continue
        

        # we should never get this far, but just in case, switch off before exit
        sock.close()
        self.heateroff()
        return
