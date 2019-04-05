#!/usr/bin/env python
'''
$Id: arduino.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Tue 29 May 2018 13:46:23 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

use the Arduino Uno as an ADC to monitor the signal generator

'''
from __future__ import division, print_function
import serial,time,multiprocessing,os,pathlib
from glob import glob
import numpy as np
from scipy.optimize import curve_fit
import datetime as dt
from satorchipy.datefunctions import tot_seconds


class arduino:
    '''
    class for running the Arduino Uno
    '''

    def __init__(self,connection='socket',port=None):
        '''
        initialize the arduino object.  We can connect by socket or by serial
        '''
        self.connection = connection.lower()
        if self.connection<>'serial': self.connection='socket'

        self.broadcast_port = 31337
        self.s = None
        self.port = port
        self.assign_logfile()
        self.assign_interrupt_flagfile()
        self.clear_interrupt_flag()

        
        if self.connection=='serial' and port is None:
            self.find_arduino()
        else:
            self.init(port)
        return None

    def assign_logfile(self):
        '''
        assign a name for the log file
        '''
        if 'HOME' in os.environ.keys():
            homedir = os.environ['HOME']
        else:
            homedir = '/tmp'
        
        logfile = homedir + os.sep + 'arduino.log'

        # test we can write to log file
        now = dt.datetime.utcnow()
        try:
            h=open(logfile,'a')
            h.write('%s | arduino assigning logfile\n' % now.strftime('%Y-%m-%d %H:%M:%S UT'))
            h.close()
            self.logfile = logfile
        except:
            print('ERROR! Could not open Arduino log file.  Messages will be printed to screen only.')
            self.logfile = None
        
        return

    def log(self,msg):
        '''
        print a message to screen and to the log file
        '''
        now=dt.datetime.utcnow()
        logmsg='%s | %s' % (now.strftime('%Y-%m-%d %H:%M:%S UT'),msg)
        if self.logfile is not None:
            h=open(self.logfile,'a')
            h.write(logmsg+'\n')
            h.close()
        print(logmsg)
        return

    def assign_interrupt_flagfile(self):
        '''
        assign an absolute path for the interrupt flag file
        '''
        if 'HOME' in os.environ.keys():
            homedir = os.environ['HOME']
        else:
            homedir = '/tmp'
            
        self.interrupt_flag_file = '%s/__ARDUINO_STOP__' % homedir
        return


    def find_arduino(self):
        '''
        search for the Arduino Uno board
        we use this if no Arduino has been specified 
        '''
        devs = glob('/dev/ttyACM*')
        if len(devs)==0:
            self.log('ERROR! No Arduino found!')
            self.port = None
            return None

        # we take the first one found
        devs.sort()
        for dev in devs:
            if self.init(dev): return

            
        return

    def init(self,port=None):
        '''
        initialize the arduino uno
        '''
        if self.connection=='serial':
            return self.init_serial(port=port)

        # nothing to do to initialize for socket connection (done in the acquire method)
        self.connected = True
        return True
    
    def init_serial(self,port=None):
        '''
        initialize the arduino device if it's a serial connection
        '''
        if port is None: port = self.port
        if port is None: port = '/dev/arduino'
        
        self.connected = False
        try:
            self.s = serial.Serial(port, 9600,timeout=0.5)
            self.port = port
        except:
            self.log('Could not connect to the Arduino Uno')
            self.s = None
            return False

        self.connected = True
        if not self.verify_acquisition():
            self.connected = False
            return False

        return True

    def is_connected(self):
        '''
        check if the arduino is connected
        '''
        if not self.connected:
            return False

        if self.connection=='socket':
            self.connected = True
            return True
        
        if self.s is None:
            self.connected = False
            return False

        if self.port is None:
            self.connected = False
            return False

        if not os.path.exists(self.port):
            self.connected = False
            return False

        if not self.verify_acquisition():
            self.connected = False
            return False

        return True


    def verify_acquisition(self):
        '''
        do a test acquisition and verify the result
        '''
        if self.s is None: return False

        # flush the line
        self.s.flush()
        
        x = self.s.readline()
        # first reading is often empty
        x = self.s.readline()

        val_str = x.strip().replace('\r','')
        if len(val_str)==0:
            self.log('ERROR! Empty response from Arduino.')
            return False
        
        try:
            val = eval(val_str)
        except:
            self.log('ERROR! Non number returned from Arduino: %s' % val_str)
            return False

        if not isinstance(val,int):
            self.log('ERROR! Invalid data type returned from Arduino: %s' % type(val))
            return False
        
        return True
    
    def acquire(self,duration=None,save=True):
        '''
        acquire data with timestamps from the Arduino Uno

        duration is given in seconds
        '''
        if not self.connected: self.init()
        if not self.connected: return None,None
        self.clear_interrupt_flag()

        if duration is None:
            dt_duration=dt.timedelta(minutes=5)
        else:
            dt_duration=dt.timedelta(seconds=duration)
        
        self.log('##### arduino_acquire #####')
        if self.connection=='serial':
            self.s.flush()
        else:            
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
            client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            client.bind(('', self.broadcast_port))

        y=[]
        t=[]
        start_time=dt.datetime.utcnow()
        end_time=start_time+dt_duration
        now=dt.datetime.utcnow()

        ## acquisition for serial connection.  Don't put the "if" inside the loop!
        if self.connection=='serial':
            while now < end_time and not os.path.isfile(self.interrupt_flag_file):
                x=self.s.readline()
                now=dt.datetime.utcnow()
                y.append(x)
                t.append(dt.datetime.utcnow())
        else:
            while now < end_time and not os.path.isfile(self.interrupt_flag_file):
                x, addr = client.recvfrom(8)
                y.append(x)
                t.append(dt.datetime.utcnow())
            

        if len(t)==0:
            if save: return None
            return None,None

        self.log('started data acquisition at %s' %  t[0].strftime('%Y-%m-%d %H:%M:%S.%f UTC'))
        self.log('  ended data acquisition at %s' % t[-1].strftime('%Y-%m-%d %H:%M:%S.%f UTC'))
        delta=t[-1]-t[0]
        self.log('total acquisition time: %.3f seconds' % tot_seconds(delta))

        arduino_a = []
        arduino_t = []
        # the first reading is always blank (?)
        for idx,val in enumerate(y):
            val_stripped=val.strip().replace('\r','')
            try:
                valno=eval(val_stripped)
                arduino_a.append(valno)
                arduino_t.append(t[idx])
            except:
                pass

        t = np.array(arduino_t)
        a = np.array(arduino_a)

        self.clear_interrupt_flag()
        
        if save:
            return self.write_data(t,a)
        
        return t,a

    def interrupt(self):
        '''
        interrupt an ongoing acquisition
        this is done simply by creating a file which acts as a flag
        '''
        try:
            pathlib.Path(self.interrupt_flag_file).touch()
        except:
            self.log('ERROR! Could not create interrupt flag file: %s' % self.interrupt_flag_file)
        return

    def clear_interrupt_flag(self):
        '''
        remove the interrupt flag file
        '''
        if os.path.isfile(self.interrupt_flag_file):
            self.log('cleaning up interrupt flag file')
            try:
                os.remove(self.interrupt_flag_file)
            except:
                self.log('WARNING: Could not remove interrupt flag file: %s' % self.interrupt_flag_file)
        return


    def write_data(self,t,v):
        '''
        write the result to file
        '''
        if len(t)==0:
            self.log('Arduino ERROR! No data.')
            return None
        
        startTime = t[0]
        outfile = startTime.strftime('calsource_%Y%m%dT%H%M%S.dat')
        h=open(outfile,'w')
        for idx,val in enumerate(v):
            tstamp = t[idx].strftime('%s.%f')
            h.write('%s %i\n' % (tstamp,val))
        h.close()
        self.log('output file written: %s' % outfile)
        return outfile

    
    def sin_curve(self,t,period,amplitude,offset,shift):
        '''
        the sine curve to fit to the modulated signal
        '''
    
        val=offset+amplitude*np.sin(2*np.pi*t/period  + shift)
        return val



    
    def fit_signal(self,t,a,period=None,amplitude=None,offset=None,shift=None):
        '''
        fit the signal data to a sine curve
        '''

        # first guess
        if period is None:period=1.0
        if amplitude is None:
            amplitude=0.5*(max(a)-min(a))
        if offset is None:
            offset=amplitude+min(a)
        if shift is None: shift=0.0
    
        p0=[period,amplitude,offset,shift]
        popt,pcov=curve_fit(sin_curve,t,a,p0=p0)
        result={}
        result['period']=popt[0]
        result['amplitude']=popt[1]
        result['offset']=popt[2]
        result['shift']=popt[3]

        return result


    #############################################################################################
    #### The following was intended to be a method within the qubicpack object
    #### to configure QUBIC via PyStudio and acquire a timeline, including data from the arduino.
    #### This will probably never be used.          #############################################
    """
    def acquire_timeline(self,go,save=True,modulation=True):
        '''
        get a data timeline and the calibration source modulation at the same time

        this will replace integrate_scientific_data() and be moved to acquisition.py
        
        '''
        client = go.connect_QubicStudio()
        if client is None:return None

        if modulation:
            manager=multiprocessing.Manager()
            arduino_a=manager.list()
            arduino_t=manager.list()
    
            arduino_proc  = multiprocessing.Process(target=self.acquire, args=(self,arduino_t,arduino_a))
            arduino_proc.start()

        if not go.exist_timeline_data():go.tdata=[]
        tdata={}
    
        go.debugmsg('calling integrate_scientific_data for ASIC %i' % go.asic)
        go.debugmsg ('integration_time=%.2f' % go.tinteg)

        npixels=go.get_NPIXELS()
        tdata['NPIXSAMP']=npixels
    
        nsamples = go.get_nsamples()
        if nsamples is None: return None
        tdata['NSAMPLES']=nsamples
    
        period = go.sample_period()
        go.debugmsg('period=%.3f msec' % (1000*period))
    
        timeline_size = int(np.ceil(go.tinteg / period))
        go.debugmsg('timeline size=%i' % timeline_size)

        chunk_size=go.get_chunksize()
        if chunk_size is None: return None
        tdata['CHUNK']=chunk_size

        bias_config=go.get_bias()
        tdata['BIAS_MIN']=go.min_bias
        tdata['BIAS_MAX']=go.max_bias
        tdata['BIAS_MOD']=go.bias_frequency
        tdata['BIASMODE']=go.bias_mode
    
        timeline = np.empty((go.NPIXELS, timeline_size))

        # date of the observation
        go.assign_obsdate()
        tdata['DATE-OBS']=go.obsdate
    
        # bath temperature
        go.oxford_read_bath_temperature()
        tdata['TES_TEMP']=go.temperature

        # feedback loop resistance (relay)
        tdata['R_FEEDBK']=go.Rfeedback

        FLL_state,FLL_P,FLL_I,FLL_D=go.get_PID()
        tdata['FLL_STAT']=FLL_state
        tdata['FLL_P']=FLL_P
        tdata['FLL_I']=FLL_I
        tdata['FLL_D']=FLL_D
        
        # integration time
        tdata['INT-TIME']=go.tinteg

        # get the rawmask from which we calculate n_masked
        rawmask=go.get_RawMask()
    
        go.debugmsg('requesting scientific data timeline...')
        parameter = 'QUBIC_PixelScientificDataTimeLine_%i' % go.QS_asic_index
        req = client.request(parameter)
        go.debugmsg('scientific data requested.')
        istart = 0
        for i in range(int(np.ceil(timeline_size / chunk_size))):
            delta = min(chunk_size, timeline_size - istart)
            go.debugmsg('getting next data chunk...',level=2)
            timeline[:, istart:istart+delta] = req.next()[:, :delta]
            go.debugmsg('got data chunk.',level=2)
            istart += chunk_size
        req.abort()
        tdata['TIMELINE']=timeline


        if modulation:
            # get the timing info from the Arduino
            arduino_proc.join()

            tdata['MOD-AMP']=arduino_a
            tdata['MOD-TIME']=arduino_t
    
        if not go.AVOID_HANGUP:
            for count in range(10):
                req.abort() # maybe we need this more than once?
            del(req) # maybe we need to obliterate this?
        
        if save:go.tdata.append(tdata)
        return timeline
       """
    



    

    
