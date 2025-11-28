'''
$Id: obsmount.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 26 Nov 2025 11:02:41 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

class to read/command the Observation mount motors
now running the PLC instead of "motorcortex" on RaspberryPi

see documentation from Luciano Ferreyro and Lucia Sucunza
ANEXO-C_command_lists_PLC.pdf
ANEXO-C_monitor_data_PLC.pdf
QUBIC_Mount_General_documentation.pdf

'''
import os,sys,socket,time,re
import datetime as dt
import numpy as np
from satorchipy.datefunctions import utcnow
from qubichk.utilities import make_errmsg, known_hosts

hk_dir = os.environ['HOME']+'/data/temperature/broadcast'
rec_fmt = '<Bdd'
rec_names = 'STX,TIMESTAMP,VALUE'    
    
class obsmount:
    '''
    class to read to and command the observation mount
    '''
    
    mount_ip = known_hosts['motorplc']
    listen_port = 9180
    command_port = 9000
    qubicstudio_port = 4003 # port for receiving data from the red platform
    qubicstudio_ip = known_hosts['qubic-studio']
    el_zero_offset = 50.0 # To Be Measured
    az_zero_offset = 0.0  # To Be Measured
    ro_zero_offset = 0.0  # To Be Measured
    tr_zero_offset = 0.0  # To Be Measured
    position_offset = {'AZ': az_zero_offset, 'EL': el_zero_offset, 'RO': ro_zero_offset, 'TR': tr_zero_offset}
    axis_fullname = {'AZ': 'azimuth', 'EL': 'elevation', 'RO': 'boresight rotation', 'TR': 'Little Train'}
    axis_keys = list(position_offset.keys())
    n_axis_keys = len(axis_keys)
    datefmt = '%Y-%m-%d-%H:%M:%S UT'
    header_keys = ['TIMESTAMP',
                   'IS_ETHERCAT',
                   'IS_SYNC',
                   'IS_MAINT',
                   'AXES_ASYNC_COUNT']
    n_header_keys = len(header_keys)

    data_keys = ['AXIS',
                 'ACT_VEL',
                 'ACT_VEL_B',
                 'ACT_POS',
                 'ACT_POS_B',
                 'ACT_TORQUE',
                 'IS_ENABLED',
                 'IS_HOMING',
                 'IS_OPERATIVE',
                 'IS_MOVING',
                 'IS_OUTOFRANGE',
                 'FAULT']
    n_data_keys = len(data_keys)


    available_commands = ['ENA',    # enable
                          'DIS',    # disable
                          'START',  # start
                          'STOP',   # stop
                          'POS',    # go to position
                          'VEL']    # set velocity
    wait = 0.0 # seconds to wait before next socket command
    default_chunksize = 512 # motor PLC sends packets of approx 200 bytes each time
    default_sampleperiod = 100 # sample period in milliseconds (Note: PLC default is 1000 msec)
    verbosity = 1
    testmode = False

    elmin = 50 # minimum permitted elevation
    elmax = 70 # maximum permitted elevation
    azmin = 0  # minimum permitted azimuth
    azmax = 25 # maximum permitted azimuth (changed to 25 on 2025-06-06 15:51:25 UT)
    azstep = 5 # default step size for azimuth movement for skydips

    pos_margin = 0.1 # default margin of precision for exiting the wait_for_arrival loop
    maxwait = 180 # default maximum wait time in seconds for wait_for_arrival loop

    
    def __init__(self):
        '''
        instantiate the class with some default values
        '''
        self.sock = {}
        self.sock['data'] = None
        self.sock['command'] = None
        self.subscribed = {}
        self.subscribed['data'] = False
        self.subscribed['command'] = False
        
        return

    def printmsg(self,msg):
        '''
        print a message to screen
        '''
        if self.verbosity<1: return
        
        date_str = utcnow().strftime(self.datefmt)
        print('%s | obsmount: %s' % (date_str,msg))
        return

    def return_with_error(self,retval):
        '''
        print a message and return the error code and stuff in a dictionary
        '''
        retval['ok'] = False
        self.printmsg('ERROR! %s' % retval['error'])
        return retval


    def do_handshake(self,port='data',sampleperiod=None):
        '''
        do the handshake with the server
        '''
        retval = {}
        retval['ok'] = False
        ack = 'NO ACK'

        if sampleperiod is None: sampleperiod = self.default_sampleperiod

        if port=='command':
            # this was the handshake with the Raspi... TO BE UPDATED
            self.printmsg('Getting acknowledgement from %s on %s port' % (self.mount_ip,port))
            try:
                ack_bin = self.sock[port].recv(4)
            except socket.timeout:
                self.subscribed[port] = False
                self.error = 'HANDSHAKE TIMEOUT'
                retval['error'] = 'Timeout error for handshake with motor %s' % port
                return self.return_with_error(retval)
            except:
                self.subscribed[port] = False
                self.error = 'HANDSHAKE FAIL'
                retval['error'] = 'Failed handshake with motor %s' % port
                return self.return_with_error(retval)
            
            
            ack = ack_bin.decode()
            if ack!='True':
                self.error = 'BAD ACK'
                self.subscribed[port] = False
                retval['error'] = 'Did not receive correct acknowledgement for %s port: %s' % (port,ack)
                return self.return_with_error(retval)
            
            time.sleep(self.wait)
            self.printmsg('sending OK')

            try:
                ans = self.sock[port].send('OK'.encode())
            except socket.timeout:
                self.subscribed[port] = False
                self.error = 'HANDSHAKE TIMEOUT ON SEND'
                retval['error'] = 'Timeout error for sending handshake to motor %s' % port
                return self.return_with_error(retval)
            except:
                self.subscribed[port] = False
                self.error = 'HANDSHAKE FAIL ON SEND'
                retval['error'] = 'Failed to send handshake to motor %s' % port
                return self.return_with_error(retval)
            # end handshake for command port

        else:
            sampleperiod_str = '%i' % sampleperiod
            try:
                nbytes = self.sock[port].send(sampleperiod_str.encode())
            except:
                retval['error'] = 'Failed to send sampling period to PLC on port %s' % port
                return self.return_with_error(retval)
            time.sleep(self.wait)
            # end handshake for data port
        
        retval['ok'] = True
        self.error = None
        self.printmsg('Handshake successful: ack=%s' % ack)
        return retval
                    
        

    def init_socket(self,port='data'):
        '''
        initialize the communication socket
        the port is either 'data' or 'command'
        '''
        retval = {}
        retval['ok'] = False
        retval['error'] = 'init error'
        self.error = None
        
        if port=='data':
            port_num = self.listen_port
            socktype = socket.SOCK_DGRAM
        else:
            port_num = self.command_port
            socktype = socket.SOCK_STREAM

        self.printmsg('creating socket with type: %s' % socktype)
        self.sock[port] = socket.socket(socket.AF_INET, socktype)
        self.sock[port].settimeout(1)
        self.printmsg('connecting to address: %s:%i' % (self.mount_ip,port_num))
        try:
            self.sock[port].connect((self.mount_ip,port_num))
        except socket.timeout:
            self.subscribed[port] = False
            self.error = 'TIMEOUT'
        except:
            self.subscribed[port] = False
            self.error = make_errmsg('SOCKET ERROR')
        else:
            retval = self.do_handshake(port)
            if not retval['ok']: return self.return_with_error(retval)
            self.subscribed[port] = True
            self.error = None                      

        if self.error is None: return True

        retval['error'] = 'could not communicate because of %s to %s:%s' % (self.error,self.mount_ip,port_num)
        return self.return_with_error(retval)

    
    def subscribe(self,port='data'):
        '''
        subscribe to the observation mount server
        the port is 'data' or 'command'
        '''

        retval = {}
        if not self.subscribed[port]:
            self.init_socket(port=port)
        
        # check that the socket is valid
        if not self.subscribed[port]:
            retval['error'] = 'could not subscribe for %s' % port
            return self.return_with_error(retval)

        return self.subscribed[port]

    def disconnect(self):
        '''
        disconnect the ports
        '''
        for port in ['data','command']:
            if not self.subscribed[port]: continue
            self.sock[port].close()
            self.sock[port] = None
            self.subscribed[port] = False
        return None

    def interpret_chunk(self,dat,retval):
        '''
        interpret the data in the chunk
        '''

        dat_str = dat.decode()
        if len(dat_str)==0:
            retval['error'] = 'no bytes received'
            self.subscribed[port] = False
            return self.return_with_error(retval)
        
        dat_list = dat_str.split('\n')
        if len(dat_list)<5:
            retval['error'] = 'partial data: %s' % dat_str
            return self.return_with_error(retval)

        axis = None
        packet = {}
        for line in dat_list:            
            col = line.split(':')
            ncols = len(col)
            if ncols==self.n_header_keys:
                for idx,val_str in enumerate(col):
                    key = self.header_keys[idx]
                    try:
                        packet[key] = eval(val_str)
                    except:
                        packet[key] = val_str
                continue

            if ncols==self.n_data_keys:
                axis = col[0]
                axis_data = {}
                for subidx,val_str in enumerate(col[1:]):
                    idx = subidx + 1
                    key = self.data_keys[idx]
                    try:
                        val = eval(val_str)
                    except:
                        val = val_str
                    axis_data[key] = val
                packet[axis] = axis_data

        packet['TIMESTAMP'] *= 0.001
        retval['DATA'] = packet
        return retval
    
    def read_data(self,chunksize=None):
        '''
        once we're subscribed, we can listen for the data
        
        The chunksize is the number of bytes to read.
        '''
        if chunksize is None: chunksize = self.default_chunksize
        port = 'data'
        retval = {}
        retval['ok'] = True
        retval['error'] = 'NONE'
        retval['CHUNK TIMESTAMP'] = utcnow().timestamp()
        for key in self.axis_keys:
            retval[key] = []

        # check that we are subscribed
        if not self.subscribed[port]:
            self.subscribe(port='data')

        if not self.subscribed[port]:
            retval['error'] = 'could not subscribe'
            return self.return_with_error(retval)

        retval['TIMESTAMP'] = utcnow().timestamp()
        try:
            dat = self.sock[port].recv(chunksize)
        except socket.timeout:
            self.subscribed[port] = False
            retval['error'] = 'socket time out'
            return self.return_with_error(retval)
        except:
            self.subscribed[port] = False
            retval['error'] = error = make_errmsg('could not get az,el data')
            return self.return_with_error(retval)

                            
        return self.interpret_chunk(dat,retval)

    def get_data(self,chunksize=None):
        '''
        this is a wrapper for read_data() because I keep forgetting
        '''
        return self.read_data(chunksize=chunksize)
    
    def send_command(self,cmd_str):
        '''
        send a command to the observation mount
        '''
        port = 'command'
        retval = {}
        retval['ok'] = True
        retval['error'] = 'NONE'
        retval['command'] = cmd_str

        # check that we are subscribed
        if not self.subscribed[port]:
            self.subscribe(port)

        if not self.subscribed[port]:
            retval['error'] = 'could not subscribe'
            return self.return_with_error(retval)

        cmd = cmd_str.split()[0].upper()
        if cmd not in self.available_commands:
            retval['error'] = 'Invalid command: %s' % cmd
            return self.return_with_error(retval)

        full_cmd_str = '%s' % cmd_str.upper()
        self.printmsg('sending command: %s' % full_cmd_str)
        if self.testmode:
            print("TESTMODE:  I didn't really send the command")
            return retval
        
        try:
            self.sock[port].send(full_cmd_str.encode())
        except:
            self.subscribed[port] = False
            retval['error'] = make_errmsg('command unsuccessful')
            return self.return_with_error(retval)

        return retval

    def dump_data(self,packet):
        '''
        write all data to binary data file
        '''
        for axis in ['AZ','EL','RO']:
            offset = self.position_offset[axis]
            rec = np.recarray(names=rec_names,formats="uint8,float64,float64",shape=(npts))
            rec.STX = 0xAA
            rec.TIMESTAMP = packet[axis]['TIMESTAMP']
            rec.VALUE = packet[axis]['ACT_POS'] + offset

            filename = '%s%s%s.dat' % (hk_dir,os.sep,axis)
            h = open(filename,'ab')
            h.write(rec)
            h.close()
            
        return True
    
    def get_azel(self,dump=False,chunksize=None):
        '''
        get the azimuth and elevation and return it with a timestamp
        '''
        retval = {}
        retval['ok'] = True
        retval['error'] = 'NONE'

        ans = self.read_data(chunksize=chunksize)
        if not ans['ok']:
            return self.return_with_error(ans)

        packet = ans['DATA']
        errmsg = []
        errlevel = 0
        retval['TIMESTAMP'] = packet['TIMESTAMP']
        retval['data'] = ans

        for axis in self.axis_keys:
            if len(packet[axis])==0:
                errmsg.append('no data for %s' % self.axis_fullname[axis])
                errlevel += 1
            else:
                retval[axis] = packet[axis]['ACT_POS'] + self.position_offset[axis]

        if dump:
            try:
                dump_ok = self.dump_data(packet)
            except:
                errmsg.append(make_errmsg('Could not dump data to file'))
                errlevel += 1
            
        if errlevel >= 2:
            retval['error'] = '\n'.join(errmsg)
            return self.return_with_error(retval)        
            
            
        return retval

    def show_azel(self):
        '''
        print the azimuth and elevation to screen
        '''
        ans = self.get_azel()
        if not ans['ok']:
            print('AZ,EL = ERROR: %s' % ans['error'])
            return False

        print('AZ,EL = %.3f %.3f' % (ans['AZ'],ans['EL']))
        return True


    def get_position(self):
        '''
        for compatibility with platform.py for the red mount
        '''
        azel = self.get_azel()
        if not azel['ok']:
            az = 'bad answer'
            el = 'bad answer'
            azwarn = True
            elwarn = True
            return az,el,azwarn,elwarn

        az = azel['AZ']
        el = azel['EL']
        azwarn = False
        elwarn = False
        return az,el,azwarn,elwarn


    def is_connected(self,port='data'):
        '''
        return status of connection
        '''
        return self.subscribed[port]

    def goto_az(self,az):
        '''
        send command to move to the given azimuth
        we correct for the encoder azimuth offset
        '''
        cmd_az = az - self.az_zero_offset
        return self.send_command('AZ %f' % cmd_az)

    def goto_el(self,el):
        '''
        send command to move to the given elevation
        we correct for the encoder elevation offset
        '''
        cmd_el = el - self.el_zero_offset
        return self.send_command('EL %f' % cmd_el)

    def stop(self):
        '''
        send command to stop movement
        '''
        return self.send_command('STOP')

    def abort(self):
        '''
        send command to abort current command
        '''
        return self.send_command('ABORT')

    def do_homing(self):
        '''
        send command to do the homing (go to the limit switch)
        '''
        return self.send_command('DOHOMING')

    def set_az_speed(self,speed):
        '''
        send command to set the azimuth speed
        '''
        cmd = 'AZS %i' % round(speed)
        return self.send_command(cmd)
    
    def set_el_speed(self,speed):
        '''
        send command to set the elevation speed
        '''
        cmd = 'ELS %i' % round(speed)
        return self.send_command(cmd)
    
    def wait_for_arrival(self,az=None,el=None,maxwait=None):
        '''
        wait for telescope to get into requested position
        '''
        tstart = dt.datetime.now().timestamp()
        if maxwait is None: maxwait = self.maxwait

        az_final = az
        el_final = el

        if (az_final is None) and (el_final is None):
            print('Please specify one of az or el with option az=<value> or el=<value>')
            return

        if az_final is not None:
            key = 'AZ'
            val_final = az_final
        else:
            key = 'EL'
            val_final = el_final

        time.sleep(2)
        azel = self.get_azel()
        
        while not azel['ok']:
            time.sleep(2)
            now = dt.datetime.now().timestamp()
            azel = self.get_azel()
            if (now-tstart)>maxwait:
                print('Error! Could not get AZ,EL position.')
                return False
        
        val = azel[key]

        while np.abs(val-val_final)>self.pos_margin:
            time.sleep(2)
            now = dt.datetime.now().timestamp()
            if (now-tstart)>maxwait:
                print('Maximum wait time')
                return False
        
            azel = self.get_azel()
            if not azel['ok']:
                time.sleep(2)
                continue

            now_str = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print('%s - AZ,EL = %.2f %.2f' % (now_str, azel['AZ'],azel['EL']))

            val = azel[key]

        return True
        
    
    def do_skydip_sequence(self,azstep=None):
        '''
        do the sky dip movements
        '''
        if azstep is None: azstep = self.azstep
    
        start_tstamp = dt.datetime.now().timestamp()

        ack = self.goto_az(self.azmin)
        if not ack['ok']:
            return False
        
        azok = self.wait_for_arrival(az=self.azmin)
        if not azok:
            print('ERROR! Did not successfully get to starting azimuth position')
            return False

        self.goto_el(self.elmin)
        elok = self.wait_for_arrival(el=self.elmin)
        if not elok:
            print('ERROR! Did not successfully get to starting elevation position')
            return False

        azel = self.get_azel()
        while not azel['ok']:
            time.sleep(2)
            azel = self.get_azel()
            now = dt.datetime.now().timestamp()
            if (now-start_tstamp)>10:
                print('ERROR! Could not get current position.')
                return False
        
        
        az = azel['AZ']
        el = azel['EL']


        for azlimit in [self.azmax, self.azmin]:
        
            while np.abs(az-azlimit)>self.pos_margin:
                self.goto_el(self.elmax)
                time.sleep(1) # wait before next command
                elok = self.wait_for_arrival(el=self.elmax)
                if not elok:
                    print('ERROR! Did not successfully get to starting elevation position')
                    return False
            

                self.goto_el(self.elmin)
                azok = self.wait_for_arrival(el=self.elmin)
                if not azok:
                    print('ERROR! Did not successfully get to starting azimuth position')
                    return False

                az += azstep
                self.goto_az(az)
                self.wait_for_arrival(az=az)

            azstep = -azstep

        return True
    
