'''
$Id: read_MCP9808_thermometer.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Tue 18 Feb 2025 07:52:53 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

Read and broadcast the temperatures in the calsource box

code used in method read_temperatures() was copied from controleverything.com
# Distributed with a free-will license.
# Use it any way you want, profit or free, provided it fits in the licenses of its associated works.
# MCP9808
# This code is designed to work with the MCP9808_I2CS I2C Mini Module available from ControlEverything.com.
# https://www.controleverything.com/content/Temperature?sku=MCP9808_I2CS#tabs-0-product_tabset-2
'''

import os,socket,time,struct
if os.uname().machine.find('arm')>=0:
    import smbus
import datetime as dt
import numpy as np
from qubichk.utilities import get_myip, get_receiver_list

# 4 sensors in the calsource box
sensors = [0,1,2,4] # these numbers correspond to which GPIO the sensor is connected
nsensors = len(sensors)
sensor_labels = ['calsource','heater','amplifier','outside']
sensor_indexes = {}
for idx,lbl in enumerate(sensor_labels):
    sensor_indexes[lbl] = idx

# data is sent as a numpy record, to be unpacked by qubic-central and QubicStudio
rec_formats = "uint8,float64,float32,float32,float32,float32"
rec_formats_list = rec_formats.split(',')
fmt = '<Bdffff'
rec_names_list = ['STX','timestamp']
for sensor in sensors:
    rec_names_list.append('T%i' % sensor)
rec_names = ','.join(rec_names_list)
rec = np.recarray(names=rec_names, formats=rec_formats,shape=(1))
rec[0].STX = 0xAA
packetsize = rec.nbytes # size of data packet broadcast on ethernet

receivers = get_receiver_list('calbox.conf')
PORT = 51337

acquisition_rate = 16.3025 # samples per second measured on 2025-03-13 at APC

def line_model(x,m,b):
    '''
    function of a straight line used for curve_fit
    '''
    y = m*x + b
    return y

class MCP9808:
    '''
    class to read/broadcast/acquire/control temperatures

    Arguments:

    broadcast_buffer: the number of temperature samples averaged together before broadcasting
    setpoint: the temperature in Kelvin where we want the calbox to be
    PID_interval: the interval time in seconds over which we calculate the integral and derivative for the PID
    PID_sensor: the name of the sensor used for measuring the temperature to control (usually 'calsource')
    Kp, Ki, Kd: gain factors for the PID
    verbosity: level of verboseness for printing to screen.  Default is 0 (no print statements, except error messages)
    
    ===========
    
    Return: runs an endless loop and does not return unless receiving a 'quit' command, or a ctrl-c interrupt
        
    '''

    def __init__(self,
                 broadcast_buffer=None,
                 setpoint=None,
                 PID_interval=None,
                 PID_sensor=None,
                 Kp=None,
                 Ki=None,
                 Kd=None,
                 verbosity=0
                 ):
        if broadcast_buffer is None:
            self.broadcast_buffer_npts = 128
        else:
            self.broadcast_buffer_npts = broadcast_buffer

        if setpoint is None:
            self.setpoint_temperature = 305.0
        else:
            self.setpoint_temperature = setpoint

        if PID_interval is None:
            self.PID_interval = 1200
        else:
            self.PID_interval = PID_interval

        if PID_sensor is None:
            self.PID_sensor = 'calsource'
        else:
            self.PID_sensor = PID_sensor

        if Kp is None:
            self.Kp = 1
        else:
            self.Kp = Kp

        if Ki is None:
            self.Ki = 1
        else:
            self.Ki = Ki

        if Kd is None:
            self.Kd = 1
        else:
            self.Kd = Kd
        
        self.verbosity_threshold = verbosity
        return

    def log(self,msg,verbosity=0):
        '''
        print a statement if we are sufficiently verbose
        '''
        if verbosity>self.verbosity_threshold: return
        print('%s|MCP9808|%s' % (dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),msg))
        return
                 
    def read_temperatures(self):
        '''
        read the MCP9808 temperatures
        '''
        temperatures = -np.ones(nsensors,dtype=float)

        # Get I2C bus
        bus = smbus.SMBus(1)

        # MCP9808 address, 0x18(24)
        # Select configuration register, 0x01(1)
        # 0x0000(00)	Continuous conversion mode, Power-up default
        config = [0x00, 0x00]
        bus.write_i2c_block_data(0x18, 0x01, config)
        # MCP9808 address, 0x18(24)
        # Select resolution rgister, 0x08(8)
        #	0x03(03)	Resolution = +0.0625 / C
        bus.write_byte_data(0x18, 0x08, 0x03)


        # MCP9808 address, 0x18(24)
        # Read data back from 0x05(5), 2 bytes
        # Temp MSB, TEMP LSB
        base_address = 0x18
        for idx,Tidx in enumerate(sensors):
            addr = base_address + Tidx

            try:
                data = bus.read_i2c_block_data(addr, 0x05, 2)
            except:
                Tkelvin = -2
            else:                        
                # Convert the data to 13-bits
                Tcelsius = ((data[0] & 0x1F) * 256) + data[1]
                if Tcelsius > 4095: Tcelsius -= 8192                
                Tcelsius *= 0.0625
                Tkelvin = Tcelsius + 273.15
            
            
            self.log("[%i] 0x%2x T%i: %.2f K" % (idx,addr,Tidx,Tkelvin),verbosity=4)
            temperatures[idx] = Tkelvin
        return temperatures

    
    def PID(self):
        '''
        calculate the Proporional-Integral-Derivative parameters
        https://en.wikipedia.org/wiki/Proportional%E2%80%93integral%E2%80%93derivative_controller

        The data is updated in broadcast_temperatures()
        '''

        # Proportional
        error_value = self.PID_temperature_buffer - self.setpoint_temperature
        P = self.Kp * error_value.mean()

        # Integral
        error_sum = error_value.sum()
        interval = self.PID_tstamp_buffer[-1] - self.PID_tstamp_buffer[0]
        I = self.Ki * error_sum / interval

        # Derivative
        fitresult = np.polyfit(self.PID_tstamp_buffer,error_value,1)
        m = fitresult[0]
        D = self.Kd * m * interval

        # Control function
        U = P + I + D

        return P,I,D,U

    def control_action(self,tstamp,control_value):
        '''
        take action according to the control value
        possible actions:
           start heater in a standard mode, or by changing the duty cycle proportion
           stop heater
           start fan
           stop fan

        for now, we just record the PID result to see what's going on
        '''
        P,I,D,U = control_value
        msg = '%17.6f %e %e %e %e\n' % (tstamp,P,I,D,U)
        self.PID_log_handle.write(msg)
        self.PID_log_handle.flush()
        return

    def broadcast_temperatures(self):
        '''
        read and broadcast the MCP9809 temperature data
        '''

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        date_now = dt.datetime.utcnow()
        date_str = date_now.strftime('%Y-%m-%d %H:%M:%S.%f')
        trycount = 0

        # parameters for the PID
        setpoint_sensor_idx = sensor_indexes[self.PID_sensor]

        # the number of points used for PID calculation is determined by:
        #    PID_interval in seconds
        #    acquisition_rate in samples per second when there is *no* buffer
        #    number of samples to fill the buffer
        PID_npts = int(np.ceil(self.PID_interval*acquisition_rate/self.broadcast_buffer_npts))
        self.PID_temperature_buffer = -np.ones(PID_npts,dtype=float)
        self.PID_tstamp_buffer = -np.ones(PID_npts,dtype=float)
        tstamp_buffer_offset = date_now.timestamp() # so we don't need double float precision
        FIFO_counter = 0

        self.PID_log_handle = open('PID_logger.txt','a')

        rec[0].STX = 0xAA
        broadcast_buffer_idx = 0
        broadcast_temperature_buffer = -np.ones((self.broadcast_buffer_npts,nsensors),dtype=float)
        logmsg_list = ['entering temperature broadcast loop',
                       'setpoint: %.2fK' % self.setpoint_temperature,
                       'sample buffer size: %i' % self.broadcast_buffer_npts,
                       'PID buffer size: %i' % PID_npts
                       ]
        self.log('\n   '.join(logmsg_list),verbosity=0)

        while True:
            try:
                temperatures = self.read_temperatures()        
            except KeyboardInterrupt:
                print('loop exit with ctrl-c')
                self.PID_log_handle.close()
                return
            except:
                trycount+=1
                if trycount>10000:
                    print('ERROR! possible I/O error.')
                    self.PID_log_handle.close()
                    return
                time.sleep(0.1)
                continue
            else:
                trycount = 0

            # add temperatures to the buffer
            broadcast_temperature_buffer[broadcast_buffer_idx,:] = temperatures
            broadcast_buffer_idx += 1

            # if we haven't filled the buffer, take another sample
            if broadcast_buffer_idx < self.broadcast_buffer_npts:
                continue
            broadcast_buffer_idx = 0

            # average the samples
            temperatures = broadcast_temperature_buffer.mean(axis=0)
                
                
            rec[0].timestamp = dt.datetime.utcnow().timestamp()
            for idx,sensor in enumerate(sensors):
                fmt_idx = idx + 2
                data_type = rec_formats_list[fmt_idx]
                val = temperatures[idx]
                cmd = 'rec[0].T%i = %f' % (sensor,val)
                self.log('%16.6f | %16s | executing: %s' % (val,data_type,cmd),verbosity=3)
                exec(cmd)
                    
            # broadcast the data
            for rx in receivers:
                self.log('%s %s' % (rx,rec),verbosity=1)
                if self.verbosity_threshold==0: time.sleep(0.05) # need a delay before sending data again
                sock.sendto(rec,(rx,PORT))

            # FIFO for PID
            self.PID_temperature_buffer = np.roll(self.PID_temperature_buffer,-1)
            self.PID_temperature_buffer[-1] = temperatures[setpoint_sensor_idx]
            self.PID_tstamp_buffer = np.roll(self.PID_tstamp_buffer,-1)
            self.PID_tstamp_buffer[-1] = rec[0].timestamp - tstamp_buffer_offset

            # if the buffer is completely filled, we continue to calculating the PID with every new sample (overkill?)
            FIFO_counter += 1
            if FIFO_counter<PID_npts: continue
            
            # PID is calculated using the buffer values (not passed as arguments)
            PID_result = self.PID()

            # decide what to do with the heater or fan
            control_result = self.control_action(rec[0].timestamp,PID_result)
    
        return

    def acquire_MCP9808_temperatures(self,listener=None):
        '''
        read the MCP9808 temperature sensors on socket and write to file
        '''
        print_fmt = '%8i: 0x%X %s %8.4fs %10.2fK %10.2fK %10.2fK %10.2fK'
    
        if listener is None: listener = get_myip()
        self.log('listening on: %s, %i' % (listener,PORT),verbosity=0)
        if listener is None:
            self.log('ERROR! Not a valid listening address.  Not connected to the network?',verbosity=0)
            return None
              
    
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        timeout = 3*self.broadcast_buffer_npts/acquisition_rate
        client.settimeout(timeout)
        client.bind((listener,PORT))
        h = open('calbox_temperatures.dat','ab')

        counter = 0
        while True:
            counter += 1
            now_tstamp = dt.datetime.now().timestamp()
            try:
                dat = client.recv(packetsize)
            except socket.timeout:
                now_str = dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                self.log('%8i: %s timeout error on socket' % (counter,now_str),verbosity=0)
                continue
            except KeyboardInterrupt:
                h.close()
                now_str = dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                self.log('%8i: %s exit using ctrl-c' % (counter,now_str),verbosity=0)
                return
            else: # continue as normal if no exception
                h.write(dat)
                h.flush()
                if self.verbosity_threshold>0:
                    dat_list = struct.unpack(fmt,dat)
                    latency = now_tstamp - dat_list[1]
                    date_str = dt.datetime.utcfromtimestamp(dat_list[1]).strftime('%Y-%m-%d %H:%M:%S.%f')
                    self.log(print_fmt % (counter,
                                          dat_list[0],
                                          date_str,
                                          latency,
                                          dat_list[2],
                                          dat_list[3],
                                          dat_list[4],
                                          dat_list[5]
                                          ),
                             verbosity=1
                             )
            

        # end of acquire_MCP9808_temperatures.  
        return
