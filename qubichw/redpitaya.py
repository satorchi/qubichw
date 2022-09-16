'''
$Id: redpitaya.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 22 Aug 14:41:36 CEST 2022
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

control the RedPitaya oscilloscope/signal-generator
'''
import time,socket,os,sys
import numpy as np
import datetime as dt
class redpitaya:
    '''
    class to control the RedPitaya oscilloscope/signal-generator
    RedPitaya SIGNALlab 250-12
    '''
    verbosity = 1

    # sample period table
    # https://redpitaya.readthedocs.io/en/latest/appsFeatures/examples/acqRF-samp-and-dec.html
    max_sample_rate = 250e6 # with decimation=1
    buffer_size = None

    current_settings = {}
    current_settings[1] = {}
    current_settings[2] = {}
    default_settings = {}
    default_settings['frequency'] = 0.7
    default_settings['shape'] = 'SINE'
    default_settings['amplitude'] = 1.0
    default_settings['offset'] = 2.0
    default_settings['duty'] = 33
    default_settings['input gain'] = 'HV'
    default_settings['acquisition units'] = 'RAW'
    default_settings['decimation'] = 65536
    default_settings['coupling'] = 'DC'
    
    # number of bytes to receive by default (but not for acquisition)
    default_settings['chunksize'] = 4096 

    # wait time after sending a command and before requesting a response
    default_settings['response delay'] = 0.05

    date_fmt = '%Y-%m-%d %H:%M:%S.%f'

    
    def __init__(self,ip=None,verbosity=None):
        '''
        initialize the RedPitaya SIGNALlab 250-12
        '''
        if verbosity is not None: self.verbosity = verbosity
        self.log('creating new object',verbosity=2)

        t = dt.datetime.utcnow()
        self.utcoffset = t.timestamp() - dt.datetime.utcfromtimestamp(t.timestamp()).timestamp()
        
        self.connection_status = False
        self.init(ip)

        return None
    
    def log(self,msg,verbosity=0):
        '''
        log message to screen and to a file
        '''
        if verbosity > self.verbosity: return
        
        filename = 'redpitaya_command.log'
        fullmsg = '%s: RedPitaya - %s' % (dt.datetime.utcnow().strftime(self.date_fmt),msg)
        h = open(filename,'a')
        h.write('%s\n' % fullmsg)
        h.close()
        print(fullmsg)
        return

    def is_connected(self):
        '''
        check if RedPitaya is currently accessible
        '''
        if not self.connection_status: return False
        id = self.get_id()
        if not self.connection_status: return False
        if id.upper().find('REDPITAYA')<0:
            self.log('ERROR! This is not the expected device: %s' % id)
            return False
        return True        

    def init(self,ip=None):
        '''
        connect to the RedPitaya
        '''
        if ip is None: ip = '192.168.1.21'
        self.ip = ip
        port    = 5000
        timeout = 0.1
        self.connection_status = False

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(timeout)
            self.sock.connect((ip, port))
            self.connection_status = True

        except:
            print('ERROR! Failed to connect to RedPitaya')
            self.connection_status = False
            return False        

        self.set_decimation(self.default_settings['decimation'])
        self.get_buffer_size()
        return None

    def send_command(self,cmd):
        '''
        send a command to the RedPitaya
        '''
        if self.verbosity>1: print('sending command: %s' % cmd)
        cmd_str = cmd + '\r\n'
        cmd_encode = cmd_str.encode()
        try:
            ans = self.sock.send(cmd_encode)
        except:
            if self.verbosity>0: print('ERROR!  Could not send to RedPitaya')
            self.connection_status = False
            return None
        
        return ans

    def get_response(self,chunksize=None,string=False):
        '''
        get the result of an inquiry command
        '''
        if chunksize is None:
            chunksize = self.default_settings['chunksize']
        try:
            ans = self.sock.recv(chunksize)
        except socket.timeout:
            self.log('ERROR! time out.  No response.',verbosity=1)
            return None
        except:
            self.log('ERROR!  Could not get reply from RedPitaya: %s' % self.sock.error,verbosity=1)
            self.connection_status = False
            return None

        
        val_str = ans.decode().replace('ERR!','').strip()
        if string: return val_str
            
        try:
            return eval(val_str)            
        except:
            return val_str
        return None


    def get_info(self,cmd,string=True):
        '''
        get info.  
        We pause before reading the response, otherwise there's a trailing byte leftover
        '''
        ans = self.send_command(cmd)
        pausetime = self.default_settings['response delay']
        time.sleep(pausetime)
        return self.get_response(string=string)

    def get_id(self):
        '''
        get the identity string
        '''
        id = self.get_info('*IDN?',string=True)
        self.current_settings['id'] = id
        return id
    
    def set_decimation(self,decimnum):
        '''
        set the decimation value:  max is 65536
        '''
        cmd = 'ACQ:DEC %i' % decimnum
        ans = self.send_command(cmd)
        return ans

    def get_decimation(self):
        '''
        get the decimation value:  max is 65536
        '''
        decnum = self.get_info('ACQ:DEC?',string=False)
        self.current_settings['decimation'] = decnum
        return decnum
    
    def get_buffer_size(self):
        '''
        get the buffer size.  This is 16384.  but in case you want the Red Pitaya to tell you...
        '''
        self.buffer_size = self.get_info('ACQ:BUF:SIZE?',string=False)
        self.current_settings['buffer size'] = self.buffer_size
        return self.buffer_size

    def get_sample_rate(self):
        '''
        calculate the sample rate given the decimation number
        sample rate is 250e6 samples/second with decimation=1 for the RedPitaya SIGNALlab 250-12
        https://redpitaya.readthedocs.io/en/latest/appsFeatures/examples/acqRF-samp-and-dec.html
        '''
        decnum = self.get_decimation()
        if decnum is None: return None

        sample_rate = self.max_sample_rate/decnum
        self.current_settings['sample rate'] = sample_rate
        return sample_rate

    def get_sample_period(self):
        '''
        the length of time to fill a buffer
        '''
        sample_rate = self.get_sample_rate()
        sample_period = self.buffer_size/sample_rate
        self.current_settings['sample period'] = sample_period
        return sample_period
        

    def get_output_state(self,ch=1):
        '''
        get the output state
        '''
        cmd = 'OUTPUT%1i:STATE?' % ch
        onoff = self.get_info(cmd,string=False)
        self.current_settings[ch]['output state'] = onoff
        return onoff

    def set_output_on(self,ch=1):
        '''
        switch on output
        '''
        cmd = 'OUTPUT%1i:STATE ON' % ch
        return self.send_command(cmd)

    def set_output_off(self,ch=1):
        '''
        switch off output
        '''
        cmd = 'OUTPUT%1i:STATE OFF' % ch
        return self.send_command(cmd)
    

    def set_frequency(self,freq,ch=1):
        '''
        set the frequency of the output
        '''
        cmd = 'SOUR%1i:FREQ:FIX %.3f' % (ch,freq)

        # we store the frequency commanded because the RedPitaya only returns a whole number for the frequency
        # even though the setting might have a fractional Hz
        self.current_settings[ch]['frequency'] = freq
        return self.send_command(cmd)

    def get_frequency(self,ch=1):
        '''
        get the current frequency
        '''
        cmd = 'SOUR%1i:FREQ:FIX?' % ch
        return self.get_info(cmd,string=False)
    
    def set_shape(self,shape,ch=1):
        '''
        set the function shape:  sine, square, etc
        '''
        if shape.upper().find('SQ')==0:
            shape = 'PWM' # use PWM to set square wave with duty cycle

        if shape.upper().find('SI')==0:
            shape = 'SINE'

        if shape.upper().find('P')==0:
            shape = 'PWM'
        
        cmd = 'SOUR%1i:FUNC %s' % (ch,shape.upper())
        return self.send_command(cmd)

    def get_shape(self,ch=1):
        '''
        get the shape
        '''
        cmd = 'SOUR%1i:FUNC?' % ch
        shape = self.get_info(cmd,string=True)
        self.current_settings[ch]['shape'] = shape

    def set_duty(self,duty,ch=1):
        '''
        set the duty cycle as a percent
        '''
        cmd ='SOUR%1i:DCYC %.4f' % (ch,duty/100)
        return self.send_command(cmd)

    def get_duty(self,ch=1):
        '''
        get the duty cycle
        '''
        cmd = 'SOUR%1i:DCYC?' % ch
        duty = self.get_info(cmd,string=False)
        self.current_settings[ch]['duty'] = duty
        return duty

    def set_offset(self,offset,ch=1):
        '''
        set the modulation offset
        '''
        cmd = 'SOUR%1i:VOLT:OFFS %.2f' % (ch,offset)
        return self.send_command(cmd)
        
    def get_offset(self,ch=1):
        '''
        get the modulation offset
        '''
        cmd = 'SOUR%1i:VOLT:OFFS?' % (ch)
        offset = self.get_info(cmd,string=False)
        self.current_settings[ch]['offset'] = offset
        return offset

    def set_amplitude(self,amplitude,ch=1):
        '''
        set the modulation amplitude
        '''
        cmd = 'SOUR%1i:VOLT %.2f' % (ch,amplitude)
        return self.send_command(cmd)
        
    def get_amplitude(self,ch=1):
        '''
        get the modulation amplitude
        '''
        cmd = 'SOUR%1i:VOLT?' % ch
        a = self.get_info(cmd,string=False)
        self.current_settings[ch]['amplitude'] = a
        return a
        

    def start_acquisition(self,ch=1):
        '''
        start the acquisition
        '''
        cmd = 'ACQ%1i:START' % ch
        return self.send_command(cmd)

    def stop_acquisition(self,ch=1):
        '''
        stop the acquisition
        '''
        cmd = 'ACQ%1i:STOP' % ch
        return self.send_command(cmd)
    

    def get_acquisition_units(self):
        '''
        get the data acquisition units, either RAW or VOLT
        '''
        cmd = 'ACQ:DATA:UNITS?'
        acqunits = self.get_info(cmd,string=True)
        self.current_settings['units'] = acqunits
        return acqunits

    def set_acquisition_units(self,units=None):
        '''
        set the data acquisition units, either RAW or VOLT
        '''
        if units is None: units = self.default_settings['acquisition units']
        cmd = 'ACQ:DATA:UNITS %s' % units.upper()
        return self.send_command(cmd)


    def set_input_gain(self,gain=None,ch=1):
        '''
        set the input gain: HV or LV (high or low)
        '''
        if gain is None: gain = self.default_settings['input gain']
        if gain.upper()=='HIGH': gain = 'HV'
        if gain.upper()=='LOW': gain = 'LV'
        cmd = 'ACQ:SOUR%1i:GAIN %s' % (ch,gain.upper())
        return self.send_command(cmd)

    def get_input_gain(self,ch=1):
        '''
        get the input gain, HV or LV (high or low)
        '''
        cmd = 'ACQ:SOUR%1i:GAIN?' % ch
        gain = self.get_info(cmd,string=True)
        self.current_settings[ch]['gain'] = gain
        return gain

    def set_input_coupling(self,coupling='DC',ch=1):
        '''
        set the input coupling:  AC or DC
        '''
        if coupling.upper()=='AC':
            coupling = 'AC'
        else:
            coupling = 'DC'
        cmd = 'ACQ:SOUR%1i:COUP %s' % (ch,coupling)
        return self.send_command(cmd)

    def get_input_coupling(self,ch=1):
        '''
        get the input coupling (AC or DC)
        '''
        cmd = 'ACQ:SOUR%1i:COUP?' % ch
        coupling = self.get_info(cmd,string=True)
        self.current_settings[ch]['coupling'] = coupling
        return coupling
        
        
    def set_default_settings(self,ch=1):
        '''
        set the default settings for a given output channel
        '''
        if not self.connection_status:
            self.log('ERROR! default settings: Device not connected')
            return False
        
        self.set_frequency(self.default_settings['frequency'],ch)
        self.set_shape(self.default_settings['shape'],ch)
        self.set_amplitude(self.default_settings['amplitude'],ch)
        self.set_offset(self.default_settings['offset'],ch)
        self.set_duty(self.default_settings['duty'],ch)
        self.set_input_gain(self.default_settings['input gain'],ch)
        self.set_acquisition_units(self.default_settings['acquisition units'])
        self.set_decimation(self.default_settings['decimation'])
        self.set_input_coupling(self.default_settings['coupling'],ch)
        self.set_output_on(ch)

        if not self.connection_status:
            self.log('ERROR! default settings: Problem setting parameters')
            return False
        
        return True

    def state(self):
        '''
        update the current settings and return the dictionary of current settings
        '''
       
        # first, the global parameters
        ans = self.get_id()
        ans = self.get_buffer_size()
        ans = self.get_acquisition_units()
        ans = self.get_decimation()
        ans = self.get_sample_period()

        # for frequency, use the last commanded value,
        # not the value returned by RedPitaya because it drops the fractional Hz
        for ch in [1,2]:
            ans = self.get_shape(ch)
            ans = self.get_amplitude(ch)
            ans = self.get_offset(ch)
            ans = self.get_duty(ch)
            ans = self.get_input_gain(ch)
            ans = self.get_output_state(ch)
            if 'frequency' not in self.current_settings[ch].keys():
                self.current_settings[ch]['frequency'] = self.get_frequency(ch)

        return self.current_settings

    def show_settings(self):
        '''
        print the current settings
        '''
        # update the dictionary settings
        ans = self.state()
        
        # print first, the global parameters
        for key in self.current_settings.keys():
            if key==1 or key==2: continue
            print(key,' = ',self.current_settings[key])

        # print the parameters for each channel
        for ch in [1,2]:
            print('-----------------')
            for key in self.current_settings[ch].keys():
                line = 'ch%i: %s = %s' % (ch,key,self.current_settings[ch][key])
                print(line)
        return

    def status(self):
        '''
        return status string compatible with calsource_configuration_manager
        '''
        # update the dictionary settings
        ans = self.state()
        msg_list = []
        # first, the global parameters
        for key in self.current_settings.keys():
            if key==1 or key==2: continue
            key_str = key.replace(' ','_')
            msg_list.append('modulator:',key,'=',self.current_settings[key])

        # the parameters for each channel
        for ch in [1,2]:
            for key in self.current_settings[ch].keys():
                key_str = key.replace(' ','_')
                msg_list.append('modulator%i:%s=%s' % (ch,key,self.current_settings[ch][key]))
                
        msg = ' '.join(msg_list)
        return msg
        
               
    def acquire(self,ch=1):
        '''
        acquire data for delta seconds
        '''
        start_tstamp = dt.datetime.utcnow().timestamp()
        sample_period = self.get_sample_period()
        
        cmd = 'ACQ:SOUR%1i:DATA?' % ch
        self.send_command(cmd)
        pausetime = self.default_settings['response delay']
        time.sleep(sample_period+pausetime)

        acq_str = self.get_response(chunksize=2**18,string=True)

        val = self.acq2array(acq_str)
        if val is None:
            return acq_str
        
        npts = len(val)
        if npts<2:
            return (start_tstamp,val)
        
        tstamps = start_tstamp + sample_period*np.arange(npts)/(npts-1)
        return (tstamps,val)

    def acq2array(self, acq_str):
        '''
        convert the string returned by the RedPitaya acquisition into a numpy array
        '''

        # check if it's a string
        if type(acq_str)!=str:
            if self.verbosity>0: print('ERROR! acquisition is expected to be type string.  This is %s' % (str(type(acq_str))))
            return None
        
        val_list = []
        vals = acq_str.replace('ERR!','').replace('{','').replace('}','').split(',')
        for valstr in vals:
            subvals = valstr.split('\n')

            for val in subvals:
                cleanval = val.strip()
                if cleanval:
                    val_list.append(float(cleanval))
        return np.array(val_list)


