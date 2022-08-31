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

    decimation = 65536
    chunksize = 4096
    wait = 0.01 # wait time after sending a command and before requesting a response

    # sample period table
    # https://redpitaya.readthedocs.io/en/latest/appsFeatures/examples/acqRF-samp-and-dec.html
    sample_rate = 250e6 # with decimation=1
    sample_period_table = {1: 6.5536e-05,
                           8: 0.000524,
                           64: 0.004194,
                           1024: 67.108e-3,
                           8192: 0.536,
                           65536: 4.294}
    
    is_connected = False


    
    def __init__(self,ip=None,verbosity=1):
        '''
        initialize the RedPitaya SIGNALlab 250-12
        '''
        t = dt.datetime.utcnow()
        self.utcoffset = t.timestamp() - dt.datetime.utcfromtimestamp(t.timestamp()).timestamp()

        self.verbosity = verbosity
        self.init_redpitaya(ip)

        
        return None


    def init_redpitaya(self,ip=None):
        '''
        connect to the RedPitaya
        '''
        if ip is None: ip = '192.168.1.21'
        self.ip = ip
        port    = 5000
        timeout = 0.1
        self.is_connected = False

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(timeout)
            self.sock.connect((ip, port))
            self.is_connected = True

        except self.sock.error:
            print('ERROR! Failed to connect to RedPitaya: %s' % self.sock.error)
            self.is_connected = False
            return False        

        self.set_decimation(self.decimation)
        return None

    def send_command(self,cmd):
        '''
        send a command to the RedPitaya
        '''
        if self.verbosity>0: print('sending command: %s' % cmd)
        cmd_str = cmd + '\r\n'
        cmd_encode = cmd_str.encode()
        try:
            ans = self.sock.send(cmd_encode)
        except:
            if self.verbosity>0: print('ERROR!  Could not send to RedPitaya')
            self.is_connected = False
            return None
        
        return ans

    def get_response(self,chunksize=None,string=False):
        '''
        get the result of an inquiry command
        '''
        if chunksize is None:
            chunksize = self.chunksize
        try:
            ans = self.sock.recv(chunksize)
        except socket.timeout:
            if self.verbosity>0: print('ERROR! time out.  No response.')
            return None
        except:
            if self.verbosity>0: print('ERROR!  Could not get reply from RedPitaya: %s' % self.sock.error)
            self.is_connected = False
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
        time.sleep(self.wait)
        return self.get_response(string=string)

    def get_id(self):
        '''
        get the identity string
        '''
        return self.get_info('*IDN?',string=True)
    
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
        return self.get_info('ACQ:DEC?',string=False)
    
    def get_buffer_size(self):
        '''
        get the buffer size.  This is 16384.  but in case you want the Red Pitaya to tell you...
        '''
        return self.get_info('ACQ:BUF:SIZE?',string=False)

    def get_sample_rate(self):
        '''
        calculate the sample rate given the decimation number
        sample rate is 250e6 samples/second with decimation=1 for the RedPitaya SIGNALlab 250-12
        https://redpitaya.readthedocs.io/en/latest/appsFeatures/examples/acqRF-samp-and-dec.html
        '''
        decnum = self.get_decimation()
        if decnum is None: return None

        if self.verbosity>2:
            print('get_sample_rate: decnum is type %s' % str(type(decnum)))
            print('get_sample_rate: decnum is %s' % decnum)
            print('get_sample_rate: slope is %f' % m)
            print('get_sample_rate: offset is %f' % b)

        sample_rate = 250e6/decnum
        return sample_rate

    def get_sample_period(self):
        '''
        the length of time to fill a buffer
        '''
        sample_rate = self.get_sample_rate()
        bufsize = self.get_buffer_size()
        sample_period = bufsize/sample_rate
        return sample_period
        

    def output_on(self,ch=1):
        '''
        switch on output
        '''
        cmd = 'OUTPUT%1i:STATE ON' % ch
        return self.send_command(cmd)

    def output_off(self,ch=1):
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
        return self.get_info(cmd,string=True)

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
        return self.get_info(cmd,string=False)

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
        return self.get_info(cmd,string=False)

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
        return self.get_info(cmd,string=False)

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
        set the data acquisition units, either RAW or VOLT
        '''
        cmd = 'ACQ:DATA:UNITS?'
        return self.get_info(cmd,string=True)

    def set_acquisition_units(self,units='RAW'):
        '''
        set the data acquisition units, either RAW or VOLT
        '''
        cmd = 'ACQ:DATA:UNITS %s' % units.upper()
        return self.send_command(cmd)
        
    
    def acquire(self,ch=1):
        '''
        acquire data for delta seconds
        '''
        start_tstamp = dt.datetime.utcnow().timestamp()
        sample_period = self.get_sample_period()
        
        cmd = 'ACQ:SOUR%1i:DATA?' % ch
        self.send_command(cmd)
        time.sleep(sample_period+self.wait)

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


