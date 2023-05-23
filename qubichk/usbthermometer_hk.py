'''
$Id: usbthermometer_hk.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 17 May 2023 21:04:26 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

receive the temperature data broadcast from the RaspberryPi with the usbthermometer
It's the temperature of the outside of the cryostat
'''
import time,socket,struct,sys
import datetime as dt
import numpy as np

class usbthermometer_hk:
    verbosity = 0

    def __init__(self,port=42377):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.client.settimeout(0.5)
        try:
            self.client.bind(('', port))
        except:
            self.client = None
            msg = ' '.join(sys.exc_info())
            print(msg)
        return

    def get_latest(self):
        '''
        get the latest data.  loop a few times to eliminate latency
        '''
        retval = {}
        retval['ok'] = False
        if self.client is None: return retval
        
        fmts = '<Bdf'
        time_diff = 1e6
        retval['ok'] = True
        for idx in range(300):
            try: 
                x, addr = self.client.recvfrom(1024)
            except:
                retval['ok'] = False
                retval['error'] = 'no broadcast from usb thermometer'
                return retval
            
            data_tuple = struct.unpack(fmts,x)
            tstamp = data_tuple[1]
            date = dt.datetime.utcfromtimestamp(tstamp)
            rx_tstamp = time.time()
            time_diff = np.abs(rx_tstamp - tstamp)
            val = data_tuple[2]
            if time_diff<0.005: break

        retval['ok'] = True
        retval['tstamp'] = tstamp
        retval['temperature'] = val
        return retval


    
