'''
$Id: modulator_siglent.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Sun 09 May 2021 18:52:58 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

remote control of the Siglent 2000 using usbtmc
Documentation in: SDG Programming Guide.pdf
see also: SDG2000X_V1.0.PDF
and: USBTMC_1_00.pdf
'''
import time,os,sys,socket,struct,string,re
import usbtmc
import datetime as dt
from qubichk.utilities import shellcommand
class siglent:
    '''
    class to send commands to the siglent signal generator using the usbtmc interface
    '''
    def  __init__(self,idVendor=0xF4EC,idProduct=0x1102,verbosity=2):
        self.verbosity = verbosity
        self.instrument = None
        self.idVendor = idVendor
        self.idProduct = idProduct
        self.state = {}
        self.state[1] = {}
        self.state[2] = {}
        self.default_settings = {}
        self.default_settings[1] = {}
        self.default_settings[1]['frequency'] = 1
        self.default_settings[1]['shape'] = 'SINE'
        self.default_settings[1]['amplitude'] = 1.0
        self.default_settings[1]['offset'] = 2.0
        self.default_settings[1]['duty'] = 50
        self.default_settings[1]['DCoffset'] = 10
        self.default_settings[1]['maximum voltage'] = 10

        # for the carbon fibre
        self.default_settings[2] = {}
        self.default_settings[2]['frequency'] = 0.3
        self.default_settings[2]['shape'] = 'SINE'
        self.default_settings[2]['amplitude'] = 2.0
        self.default_settings[2]['offset'] = 1.0
        self.default_settings[2]['duty'] = 50
        self.default_settings[2]['DCoffset'] = 10
        self.default_settings[2]['maximum voltage'] = 10

        self.date_fmt = '%Y-%m-%d %H:%M:%S.%f'

        self.log('SIGLENT:  creating new siglent modulator object')
        self.init()
        return None
    
    def log(self,msg,verbosity=0):
        '''
        log message to screen and to a file
        '''
        if verbosity > self.verbosity: return
        
        filename = 'siglent_command.log'
        h = open(filename,'a')
        h.write('%s: %s\n' % (dt.datetime.utcnow().strftime(self.date_fmt),msg))
        h.close()
        print(msg)
        return

    def init(self):
        '''
        establish connection to the Siglent waveform generator
        '''
        init_str = 'USB::0x%04X::0x%04X::INSTR' % (self.idVendor,self.idProduct)
        dev = '/dev/siglent'
        
        # wait for device to appear
        start_time = dt.datetime.utcnow()
        end_time = start_time + dt.timedelta(seconds=45)
        self.log('waiting for %s' % dev)
        while not os.path.exists(dev) and dt.datetime.utcnow()<end_time:
            time.sleep(1)
        waited = dt.datetime.utcnow() - start_time
        self.log('waited %.1f seconds for device %s' % (waited.total_seconds(),dev))

        # now try a few times to connect
        attempt_counter = 0
        while (self.instrument is None and attempt_counter<5):
            attempt_counter += 1
            del(self.instrument)
            self.instrument = None
            self.log('modulator: Establishing communication with the Siglent wave generator: %s' % init_str)
            try:
                self.instrument =  usbtmc.Instrument(init_str)
            except:
                self.log('modulator: Could not connect!\n  %s\n  %s\n  %s' % sys.exc_info())
                if os.path.exists(dev):
                    self.log('modulator: path exists: %s' % dev)
                    cmd = 'udevadm info -a %s' % dev
                    out,err = shellcommand(cmd)
                    sections = out.split('looking at ')
                    dev = sections[1].split('\n')[0].split(' ')[-1][1:-2]
                    devinfo = [dev]
                    for line in sections[1].split('\n'):
                        if line.find('serial')>0:
                            devinfo.append(line)
                            continue
                        if line.find('idProduct')>0:
                            devinfo.append(line)
                            continue
                        if line.find('idVendor')>0:
                            devinfo.append(line)
                            continue
                        if line.find('manufacturer')>0:
                            devinfo.append(line)
                            continue
                        if line.find('product')>0:
                            devinfo.append(line)
                            continue
                        
                    self.log('\n'.join(devinfo))
                
                else:
                    self.log('modulator: no device %s' % dev)

        if self.instrument is None: return None

        # verify ID, first first request always craps out
        try:
            self.log('modulator:  making first ID request')
            id = self.instrument.ask("*IDN?\r\n")
        except:
            time.sleep(0.3)

        try:
            self.log('modulator:  making second ID request')
            id = self.instrument.ask("*IDN?\r\n")
        except:
            self.log('modulator ERROR!  did not succeed with second ID request.')
            del(self.instrument)
            self.instrument = None
            return None
        
        if id is None or id=='':
            self.log('modulator ERROR! did not return a valid ID: %s' % id)
            return None
        self.log('modulator: The device says: %s' % id)
        
        return

    def is_connected(self):
        '''
        check if the signal generator is connected
        '''

        if self.instrument is None:
            self.log('SIGLENT is not initiated')
            return False

        id = self.ask_id()
        if id is None or id=='':
            self.log("modulator: did not return it's ID.")

            # try again one more time
            time.sleep(0.5)
            id = self.ask_id()
            if id is None or id=='':
                self.log("modulator: did not return it's ID after second time.")
                return False

        return True

    def send_command(self,cmd):
        '''
        send a command to the modulator
        if it's a query, use the "ask" method, otherwise use the "write" method
        '''
        if cmd.find('?')>0:
            query = True
        else:
            query = False
            ans = 'SUCCESS'
    
        try:
            if query: ans = self.instrument.ask('%s\r\n' % cmd)
            else: self.instrument.write('%s\r\n' % cmd)
        except:
            str_list = [cmd]
            for info in sys.exc_info():
                str_list.append(str(info))
            self.log('modulator: Command unsuccessful!  %s' % '  \n'.join(str_list))
            return None
        return ans


    def ask_id(self):
        '''
        ask for the id of the intrument and return it
        '''
        id = self.send_command("*IDN?")
        return id



    def read_settings(self,channel=1,show=True,full_response=False):
        '''
        read the current settings of the Siglent waveform generator
        example return string:  C1:BSWV WVTP,SINE,FRQ,100HZ,PERI,0.01S,AMP,2V,OFST,0V,HLEV,1V,LLEV,-1V,PHSE,0

        show, full_response: for compatibility with modulator_tg5012a
        '''
        if not self.is_connected():  return None
        settings = {}

        cmd = 'C%i:BSWV?' % channel
        ans = self.send_command(cmd)
        if ans is None: return None

        
        setting_str = ans.split(' ')[1]
        setting_list = setting_str.split(',')
        nsettings = len(setting_list)//2
        for idx in range(nsettings):
            key = setting_list[2*idx]
            val = setting_list[2*idx+1]
            settings[key] = val
        settings['output'] = self.get_output_state(channel)

        # translate SIGLENT names to what is expected by the calsource_manager
        siglent_translation = {'AMP': 'amplitude',
                               'FRQ': 'frequency',
                               'OFST': 'offset',
                               'DUTY': 'duty',
                               'WVTP': 'shape'}
        for key in siglent_translation.keys():
            if key in settings.keys():
                settings[siglent_translation[key]] = settings[key]
            else:
                settings[siglent_translation[key]] = None
            
        self.settings = settings
        return settings
   
    def configure(self,frequency=None,shape=None,amplitude=None,offset=None,duty=None,output=None,channel=1):
        '''
        configure the Siglent waveform generator
        
        Frequency is given in Hz
        The wave form can be: SINE, SQUARE, RAMP, PULSE, NOISE, ARB, DC, PRBS, IQ

        '''
        if not self.is_connected():
            return None
        
        # switch off output while reconfiguring
        output_state = self.get_output_state(channel)
        self.set_output_off(channel)        

        # # do we want default settings?
        # if frequency is None\
        #    and shape is None\
        #    and amplitude is None\
        #    and offset is None\
        #    and duty is None\
        #    and output is None:
        #     self.set_default_settings(channel)
        #     self.set_output_on(channel)
        #     return True

        # otherwise, set each parameter requested
        if frequency is not None:
            self.set_frequency(frequency,channel)
            time.sleep(0.5)
        if shape is not None:
            # matching the old commands to the new ones
            if shape.upper().find('SQ') >= 0: shape='SQUARE'
            if shape.upper().find('SI') >= 0: shape='SINE'
            if shape.upper().find('TRI') >= 0: shape='RAMP'
            self.set_shape(shape,channel)
            time.sleep(0.5)
        if amplitude is not None:
            self.set_amplitude(amplitude,channel)
            time.sleep(0.5)
        if offset is not None:
            self.set_offset(offset,channel)
            time.sleep(0.5)
        if duty is not None:
            self.set_duty(duty,channel)
            time.sleep(0.5)

        # restore output state or reset output state as required
        if (output is None and output_state=='ON') or output.upper()=='ON':
            self.set_output_on(channel)

        return True


    def set_output_off(self,channel=1):
        cmd = 'C%i:OUTP STATE,OFF' % channel
        ans = self.send_command(cmd)
        return ans

    def set_output_on(self,channel=1):
        cmd = 'C%i:OUTP STATE,ON' % channel
        ans = self.send_command(cmd)
        return ans

    def set_frequency(self,frequency,channel=1):
        cmd = "C%i:BSWV FRQ,%.2f" % (channel,frequency)
        ans = self.send_command(cmd)
        self.state[channel]['frequency'] = frequency
        return ans

    def set_shape(self,shape,channel=1):
        cmd = "C%i:BSWV WVTP,%s" % (channel,shape)
        ans = self.send_command(cmd)
        self.state[channel]['shape'] = shape
        return ans

    def set_amplitude(self,amplitude,channel=1):
        cmd = "C%i:BSWV AMP,%.2f" % (channel,amplitude)
        ans = self.send_command(cmd)
        self.state[channel]['amplitude'] = amplitude
        return ans

    def set_offset(self,offset,channel=1):
        cmd = "C%i:BSWV OFST,%.2f" % (channel,offset)
        ans = self.send_command(cmd)
        self.state[channel]['offset'] = offset
        return ans
    
    def set_duty(self,duty,channel=1):
        cmd = "C%i:BSWV DUTY,%.2f" % (channel,duty)
        ans = self.send_command(cmd)
        self.state[channel]['duty'] = duty
        return ans

    def set_max_voltage(self,maximum_voltage,channel=1):
        cmd = "C%i:BSWV MAX_OUTPUT_AMP,%.2f" % (channel,maximum_voltage)
        ans = self.send_command(cmd)
        self.state[channel]['maximum output amplitude'] = maximum_voltage
        return ans
        

    def get_output_state(self,channel=1):
        '''
        get output state
        example return string: 'C1:OUTP OFF,LOAD,HZ,PLRT,NOR'
        '''
        cmd = "C%i:OUTP?" % channel
        ans = self.send_command(cmd)
        if ans is None: return None
        output_state = ans.split(' ')[1].split(',')[0]
        self.state[channel]['output'] = output_state
        return output_state
        

    def set_default_settings(self,channel=1):
        '''
        configure with default settings
        '''
        self.log('modulator: setting default settings for channel %i' % channel)

        if not self.is_connected():
            self.log('modulator: asked for default settings but not connected.  Trying to connect.')
            self.init()

        if not self.is_connected():
            self.log('modulator is not connected.  Cannot set default settings.')
            return False

        self.send_command('C%i:OUTP LOAD,50' % channel) # default 50 Ohm load
        self.set_frequency(self.default_settings[channel]['frequency'],channel)
        self.set_shape(self.default_settings[channel]['shape'],channel)
        self.set_amplitude(self.default_settings[channel]['amplitude'],channel)
        self.set_offset(self.default_settings[channel]['offset'],channel)
        self.set_duty(self.default_settings[channel]['duty'],channel)
        self.set_max_voltage(self.default_settings[channel]['maximum voltage'],channel)
        self.set_output_on(channel)
        return True

    def disconnect(self):
        self.log("disconnecting the instrument")
        self.instrument.close()
        return


    
