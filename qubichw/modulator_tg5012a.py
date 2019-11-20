'''
$Id: modulator_tg5012a.py
$auth: Manuel Gonzalez
$created: Thu, 11 Apr 2019 17:41:26
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

remote control of the TTi 5012A Signal Generator
'''
from __future__ import division, print_function
import time,os,sys,socket,struct,string,re
import datetime as dt
from PyMS import PMSDevice

class tg5012:
    '''
    class to send commands to the tti 5012A signal generator
    '''
    def  __init__(self,ip='192.168.2.16',port=9221):
        print('New instance of tg5012 modulator class')
        self.energenie = None
        self.ip = ip
        self.port = port
        self.state = {}
        self.default_settings = {}
        self.default_settings['frequency'] = 1
        self.default_settings['shape'] = 'SINE'
        self.default_settings['amplitude'] = 2
        self.default_settings['offset'] = 2.5
        self.default_settings['duty'] = 50
        self.default_settings['DCoffset'] = 10
        
        self.maximum_voltage = 10

        self.s = None
        return None
    
    def is_connected(self):
        '''
        check if the signal generator is connected
        '''
        if self.s is None:
            # try to connect
            self.init_tg5012a()

        if self.s is None:
            return False

        id = self.ask_id()
        if id=='':  return False

        return True

    def send_command(self,cmd):
        '''
        send a command to the modulator
        '''
        try:
            self.s.send(cmd.encode())
        except:
            return False
        return True

    def read_response(self):
        '''
        read response from the instrument to a single command
        '''
        finished = False
        answer=[]
        while not finished:
            try:
                ans = self.s.recv(1)
                answer.append(ans.decode())
            except socket.timeout:
                finished = True
            except:
                print('could not decode: %s' % ans)
                #finished = True
        return ''.join(answer)

    def ask_id(self):
        '''
        ask for the id of the intrument and return it
        '''
        self.send_command("*IDN?\n")
        answer=self.read_response()
        return answer

    def switchon(self):
        '''
        use the Energenie smart powerbar to switch on the power to the modulator
        '''

        # open Energenie device with hostname and password
        if self.energenie is None:
            self.energenie = PMSDevice('energenie', '1')

        # switch on
        self.energenie.set_socket_states({0:True})

        return

    def switchoff(self):
        '''
        use the Energenie smart powerbar to switch off the power to the modulator
        '''

        # open Energenie device with hostname and password
        if self.energenie is None:
            self.energenie = PMSDevice('energenie', '1')

        # switch on
        self.energenie.set_socket_states({0:False})

        return    

    def init_tg5012a(self,port=None,ip=None):
        '''
        establish connection to the TTi 5012A waveform generator
        usually in ip 192.168.2.16:9221
        '''
        if port is None: port = self.port
        if ip is None: ip = self.ip

        s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        try: 
            s.connect((ip,port))
        except socket.error:
            #print("Caught exception socket.error")
            return None
        print('Establishing communication with the TTi 5012A wave generator on ip:port: %s:%d\n'% (ip,port))
        self.s = s
        sockname = s.getsockname()
        print("init_tg5012a() socket: (%s,%i)" % sockname)
        id = self.ask_id()
        if id=='':
            print('ERROR! unable to communicate!')
            return None
        print('The device says: %s\n' % id)
        
        return s

    def read_settings(self,show=True,full_response=False):
        '''
        read the current settings of the TTi 5012A waveform generator
        '''
        if not self.is_connected():  return None
        self.settings = {}

        debugfile = open('modulator_tg5012a.debug.log','a')
        
        self.send_command("*LRN?\n")
        self.answer1 = self.read_response()
        self.send_command("*WAI\n")                   #We do this to get the full response to the LRN? command
        self.answer2 = self.read_response()
        self.answer = self.answer1 + self.answer2
        # correct some weirdness in the answer
        answer = filter(lambda x: x in string.printable, self.answer)
        answer = answer.replace('Hzzz','Hz').replace('Hzz','Hz').replace('HzHz','Hz').replace('mHzkHz','mHz')
        answer_list = re.split('[+-]',answer)
        id_list = {}
        id_list[1]  = 'frequency'
        id_list[5]  = 'amplitude'
        id_list[9]  = 'offset'
        id_list[13] = 'duty'
        id_list[33] = 'dc offset'
        debugfile.write('\nDEBUG read_settings: %s' % dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
        for idx,item in enumerate(answer_list):
            clean_item = re.sub(' \.$','',item)
            item_id = 'unknown'
            if idx in id_list.keys():
                item_id = id_list[idx]
                match = re.search('[a-zA-Z%]',item)
                if match:
                    val_str = item[:match.start()]
                    val = eval(val_str)
                    units = item[match.start():].replace('Hzzz','Hz').replace('Hzz','Hz').replace('HzHz','Hz').replace('mHzkHz','mHz')
                    clean_item = '%+06f %s' % (val,units)
                    self.settings[item_id] = '%+06f%s' % (val,units)
            debugfile.write('\n%02i: %12s: %s' % (idx,item_id,clean_item))

            
        debugfile.write('\n=============================\n')
        debugfile.close()
        
        try:
            #Byte 918 of the response has the information of the wave shape 0=SINE, 1=SQUARE, etc.
            self.shape_value = ord(struct.unpack("c",self.answer[918])[0]) 
        except:
            print("Error while reading the shape")
            self.shape_value = -1

        self.shape_dict = {
            0: 'SINE',
            1: 'SQUARE',
            2: 'RAMP',
            5: 'DC'
                }

        self.settings['shape'] = self.shape_dict.get(self.shape_value, "UNKNOWN")
        # Filtering non printable characters and an s at the beginning
        if(self.settings['shape'] ==  'DC'):
            #self.settings['offset'] = filter(lambda x: x in string.printable, self.answer[923:950])
            self.settings['offset'] = self.settings['dc offset']
            self.settings['amplitude'] = '--'
            self.settings['frequency'] = '--'
            self.settings['duty']='--'
        '''
        else:
            self.settings['amplitude'] = filter(lambda x: x in string.printable, self.answer[128:156]).replace(' ','')
            self.settings['frequency'] = filter(lambda x :x in string.printable, self.answer[8:36]).replace(' ','')
            self.settings['offset'] = filter(lambda x :x in string.printable, self.answer[244:272]).replace(' ','')
            self.settings['duty'] = filter(lambda x :x in string.printable, self.answer[356:384]).replace(' ','')
        '''
    
        if show:
            print("Shape:%s" % self.settings['shape'])
            print("Frequency:%s" % self.settings['frequency'])
            print("Amplitude:%s" % self.settings['amplitude'])
            print("Offset:%s" % self.settings['offset'])
            print("Duty:%s" % self.settings['duty'])
        
        if full_response:
            return self.answer
        else:
            return self.settings
   
    def configure(self,frequency=None,shape=None,amplitude=None,offset=None,duty=None):
        '''
        configure the TTI tg5012 waveform generator
        
        Frequency is given in Hz
        The wave form can be: SIN, SQU, TRI,     
        '''
        if not self.is_connected():
            return None
        
        '''
        Check if DC shape is required for no time modulation. In this case amplitude, duty and frequency are ignored
        '''
        if shape and shape.upper()=="DC":
            self.set_modulation_off(offset)
            return True
        
        '''
        Check that the maximum voltage is not exceed
        '''

        ##### we need to get the amplitude as a number to do this
        ##### anyway, the TTi 5012A cannot output more than 10V
        #if amplitude + abs(offset) > self.maximum_voltage:
        #    print("Maximum voltage exceeded. Setting default values")
        #    self.set_default_settings()
        #    return True

        self.set_output_off()

        if frequency is None\
           and shape is None\
           and amplitude is None\
           and offset is None\
           and duty is None:
            self.set_default_settings()
            self.set_output_on()
            return
                
        if frequency:
            self.set_frequency(frequency)
            time.sleep(0.5)
        if shape:
            # matching the old commands to the new ones
            if shape.upper().find('SQ') >= 0: shape='SQUARE'
            if shape.upper().find('SI') >= 0: shape='SINE'
            if shape.upper().find('TRI') >= 0: shape='RAMP'
            self.set_shape(shape)
            time.sleep(0.5)
        if amplitude:
            self.set_amplitude(amplitude)
            time.sleep(0.5)
        if offset:
            self.set_offset(offset)
            time.sleep(0.5)
        if duty:
            self.set_duty(duty)
            time.sleep(0.5)

        self.set_output_on()

        return True

    def set_modulation_off(self, offset):
        self.set_output_off()
        self.send_command("WAVE ARB\n")
        self.send_command("ARBLOAD DC\n")
        if offset: self.send_command("ARBDCOFFS %.2f\n" % offset)
        self.set_output_on()

    def set_output_off(self):
        self.send_command("OUTPUT OFF\n")

    def set_output_on(self):
        self.send_command("OUTPUT ON\n")

    def set_default_settings(self):
        '''
        configure with default settings
        '''
        if not self.is_connected():
            return None

        self.set_frequency(self.default_settings['frequency'])
        self.set_shape(self.default_settings['shape'])
        self.set_amplitude(self.default_settings['amplitude'])
        self.set_offset(self.default_settings['offset'])
        self.set_duty(self.default_settings['duty'])
        return True

    def set_frequency(self,frequency):
        self.send_command("FREQ %.5f\n" % frequency)
        self.state['frequency'] = frequency
        return True

    def set_shape(self,shape):
        self.send_command("WAVE %s\n" % shape)
        self.state['shape'] = shape
        return True

    def set_amplitude(self,amplitude):
        self.send_command("AMPL %.2f\n" % amplitude)
        self.state['amplitude'] = amplitude
        return True

    def set_offset(self,offset):
        self.send_command("DCOFFS %.2f\n" % offset)
        self.send_command("ARBDCOFFS %.2f\n" % offset)
        self.state['offset'] = offset
        return True
    
    def set_duty(self,duty):
        self.send_command("SQRSYMM %.2f\n" % duty)
        self.state['duty'] = duty
        return True

    def tg5012a_disconnect():
        print("disconnecting the instrument")
        self.s.close()

    def run_commands(self,parms):
        '''
        run a list of commands given by the dictionary "parms"
        parms.keys() should have all the keywords used in self.configure()
        '''

        # some debug text
        #print("here are the commands I've received:\n")
        #for key in parms.keys():
        #    print('  %s: %s\n' % (key,parms[key]))
        
        
        if parms['help']:
            self.help()
            return
        
        if parms['onoff'] == 'off':
            self.switchoff()
            return

        if parms['onoff'] == 'on':
            self.switchon()

        if parms['status'] == 'show':
            self.read_settings(show=True)
            return

        if parms['default']:
            self.configure()
            return
        
        
        self.configure(frequency=parms['frequency'],
                       shape=parms['shape'],
                       amplitude=parms['amplitude'],
                       offset=parms['offset'],
                       duty=parms['duty'])

        time.sleep(0.2)
        self.read_settings(show=True)
        return

    def parseargs(self,argslist):
        '''
        interpret a list of commands and return a dictionary of commands to use in run_commands()
        '''
        
        # initialize
        parms = {}
        numerical_keys = ['frequency','freq','f','amplitude','a','offset','o','duty','d']
        str_keys = ['shape','sh','status','onoff','quit','default','help']
        keys = numerical_keys + str_keys
        for key in keys:
            parms[key]=None

        # if no arguments, just show status
        if not argslist:
            parms['status'] = 'show'

        # parse argslist
        for arg in argslist:
            arg = arg.lower()
            for key in numerical_keys:
                findstr = '%s=' % key
                if arg.find(findstr)==0:
                    if key=='freq' or key=='f':
                        key='frequency'
                    if key=='a': key='amplitude'
                    if key=='o': key='offset'
                    if key=='d': key='duty'
                    if key=='s': key='status'
                    if key=='sh': key='shape'
                    vals = arg.split('=')
                    try:
                        val = eval(vals[1])
                        parms[key] = val
                            
                    except:
                        print('invalid %s' % key)

            for key in str_keys:
                findstr = '%s=' % key
                if arg.find(findstr)==0:
                    vals = arg.split('=')
                    val = vals[1].upper()
                    parms[key] = val

            # toggle type keywords
            if arg=='status':
                parms['status'] = 'show'
                continue

            if arg=='default' or arg=='init':
                parms['default'] = True
                continue
            
            if arg=='on':
                parms['onoff'] = 'on'
                continue

            if arg=='off':
                parms['onoff'] = 'off'
                continue

            if arg=='q' or arg=='quit' or arg=='exit':
                parms['quit'] = True
                continue

            if arg=='help' or arg=='h':
                parms['help'] = True
                continue

        return parms

    def help(self):
        '''
        print some help about valid commands
        '''
        helptxt =  '\ncommands:\n'
        helptxt += '\nfrequency=<N> : frequency is given in Hz (default 1Hz)'
        helptxt += '\namplitude=<N> : amplitude in V (default 5V)'
        helptxt += '\noffset=<N>    : offset in V (default 2.5V)'
        helptxt += '\nduty=<N>      : duty cycle in percent (default 50%)'
        helptxt += '\nshape=<S>     : shape is one of "SQU, SIN, TRI (default SQU)'
        helptxt += '\ndefault       : setup default values for the signal generator'
        helptxt += '\nstatus        : print out the current settings'
        helptxt += '\non            : switch on the signal generator'
        helptxt += '\noff           : switch off the signal generator'
        helptxt += '\nquit          : quit the program'

        print(helptxt)
                
        return

    def command_loop(self,argstr=None):
        '''
        a command line interface to the modulator
        '''

        # initially, use command line arguments at invocation
        if argstr is None:
            argslist = sys.argv
        else:
            argslist = argstr.strip().split()
        
        parms = self.parseargs(argslist)
        while not parms['quit']:
            self.run_commands(parms)
            ans=raw_input('Enter command ("help" for list): ')
            argslist = ans.strip().split()
            parms = self.parseargs(argslist)

        return

