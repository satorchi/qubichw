'''$Id: obsmount.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 07 Dec 2022 18:18:20 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

class to read/command the Observation mount motors

motor interface developed by Carlos Reyes and Luciano Ferreyro

email from Carlos, 2022-12-07 17:25:40
email from Carlos, 2023-05-15 05:46:57

The data obtained after the subscribe method will be:

DATA:TIMESTAMP:AXIS:ACT_VELOCITY:TARGET_VELOCITY:ACT_POSITION:TARGET_POSITION:ACT_TORQUE:IS_READY:IS_HOMED:AXIS_STATUSWORD:ERROR_CODE:WARNING_BITS:GLOBAL_DRIVER_STATE

example:
1682446097.96:AZ:0:0:1.0101177366738976:0.0:False:1:1

DATA: keyword to separate data packages

TIMESTAMP: seconds since 1970-01-01

AXIS: AZ or EL

ACT_VELOCITY: actual velocity (this is the actual value that KEB
              driver calculates)

TARGET_VELOCITY: target velocity that will be using while motor is
                 running

ACT_POSITION: actual position. This value is already converted via a
              calibration constant and should be a float. 0 means that
              the axis is near the lower limit switch and will be
              touching the homing switch (not yet activating it).

TARGET_POSITION: the last target position that was written into the
                 KEB driver.

ACT_TORQUE:

IS_READY: this is a bit from the StatusWord of the KEB driver and
          means that it is ready for operation (no exception was
          raised)......maybe this is too obvious.

IS_HOMED: this is a boolean variable from the program and not from the
          StatusWord. The server app has no memory and the
          HomingRoutine should be executed every time the system is
          restarted. This decision was committed thinking about system
          security.

AXIS_STATUSWORD: 16bit StatusWord of the axis driver

ERROR_CODE:

WARNING_BITS:

GLOBAL_DRIVER_STATE

In order to subscribe to the update service you should send the "OK" message to
the RPi to the 4546 port. After that you will start receiving messages with the
above structure every 100ms.

The IP for the rpi running the server is 192.168.2.103.  4545 is
listening for commands but 4546 is listening for incoming subscribers.


------------------ available commands --------------------------
'AZ <n>' send to absolute azimuth position (see zero offset below)
'EL <n>' send to absolute elevation position (see zero offset below)
'DOHOMING' go home (absolute az 0, el 41.6 see below)
'STOP' stop moving now 
'ABORT' abort current command (and reset?)


------------------ zero measurements --------------------------
2023-04-14 17:20:29
elevation commanded to 8.5 degrees is 50.1 degrees elevation

2023-04-19 08:18:57
raw elevation: 17.952062612098484 is 50 degrees elevation

2023-04-26 13:39:49
raw elevation:  10.58209685308984 is 50 degrees elevation

2023-05-10 09:17:06
raw elevation:  2.049 is 50 degrees elevation

2023-05-23 18:26:00
azimuth offset
on rocketchat from Manuel Platino: The most precise measurement of the az from outside is between 168° and 169°

'''
import os,sys,socket,time,re
import datetime as dt
import numpy as np
from qubichk.utilities import make_errmsg

hk_dir = os.environ['HOME']+'/data/temperature/broadcast'
rec_fmt = '<Bdd'
rec_names = 'STX,TIMESTAMP,VALUE'    
    
class obsmount:
    '''
    class to read to and command the observation mount
    '''
    
    mount_ip = '192.168.2.103'
    listen_port = 4546
    command_port = 4545
    el_zero_offset = 50 - 2.049
    az_zero_offset = 168.5
    datefmt = '%Y-%m-%d-%H:%M:%S UT'
    data_keys = ['TIMESTAMP',
                 'AXIS',
                 'ACT_VELOCITY',
                 'TARGET_VELOCITY',
                 'ACT_POSITION',
                 'TARGET_POSITION',
                 'ACT_TORQUE',
                 'IS_READY',
                 'IS_HOMED',
                 'AXIS_STATUSWORD',
                 'ERROR_CODE',
                 'WARNING_BITS',
                 'GLOBAL_DRIVER_STATE']
    nkeys = len(data_keys)
    available_commands = ['AZ',       # move to azimuth
                          'EL',       # move to elevation
                          'ROT',      # move to rotation (bore-sight)
                          'AZS',      # set azimuth speed
                          'ELS',      # set elevation speed
                          'DOHOMING', # go to home position
                          'STOP',     # stop
                          'ABORT',    # abort command.  motors will show an alert status
                          'END'       # end connection (unsubscribe)
                          ]
    wait = 0.0 # seconds to wait before next socket command
    default_chunksize = 131072
    verbosity = 1
    testmode = False

    elmin = 50 # minimum permitted elevation
    elmax = 70 # maximum permitted elevation
    azmin = 0  # minimum permitted azimuth
    azmax = 15 # maximum permitted azimuth
    azstep = 5 # default step size for azimuth movement for skydips

    pos_margin = 0.1 # default margin of precision for exiting the wait_for_arrival loop
    maxwait = 120 # default maximum wait time in seconds for wait_for_arrival loop

    
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
        
        date_str = dt.datetime.utcnow().strftime(self.datefmt)
        print('%s | obsmount: %s' % (date_str,msg))
        return

    def return_with_error(self,retval):
        '''
        print a message and return the error code and stuff in a dictionary
        '''
        retval['ok'] = False
        self.printmsg('ERROR! %s' % retval['error'])
        return retval


    def do_handshake(self,port='data'):
        '''
        do the handshake with the server
        '''
        retval = {}
        retval['ok'] = False
        ack = 'NO ACK'

        if port=='command':
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
            socktype = socket.SOCK_STREAM
        else:
            port_num = self.command_port
            socktype = socket.SOCK_STREAM

        self.printmsg('creating socket with type: %s' % socktype)
        self.sock[port] = socket.socket(socket.AF_INET, socktype)
        self.sock[port].settimeout(1)
        try:
            self.printmsg('connecting to address: %s:%i' % (self.mount_ip,port_num))
            self.sock[port].connect((self.mount_ip,port_num))
            retval = self.do_handshake(port)
            if not retval['ok']: return self.return_with_error(retval)
            
            self.subscribed[port] = True
            self.error = None
        except socket.timeout:
            self.subscribed[port] = False
            self.error = 'TIMEOUT'
        except:
            self.subscribed[port] = False
            self.error = make_errmsg('SOCKET ERROR')

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
        retval['TIMESTAMP'] = dt.datetime.utcnow().timestamp()

        # check that we are subscribed
        if not self.subscribed[port]:
            self.subscribe(port='data')

        if not self.subscribed[port]:
            retval['error'] = 'could not subscribe'
            return self.return_with_error(retval)

        retval['TIMESTAMP'] = dt.datetime.utcnow().timestamp()
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

                            

        dat_str = dat.decode()
        if len(dat_str)==0:
            retval['error'] = 'no bytes received'
            self.subscribed[port] = False
            return self.return_with_error(retval)
        
        dat_list = dat_str.split('DATA:')
        if len(dat_list)<3:
            retval['error'] = 'partial data: %s' % dat_str
            return self.return_with_error(retval)
        
        # remove the first and last which could be partial
        del(dat_list[0])
        del(dat_list[-1])

        retval['AZ'] = []
        retval['EL'] = []

        for line in dat_list:
            col = line.split(':')
            
            data = {}
            for idx,key in enumerate(self.data_keys):
                if key=='AXIS':
                    data[key] = col[idx]
                    continue

                try:
                    data[key] = eval(col[idx])
                except:
                    retval['data'] = data
                    retval['error'] = error = make_errmsg('could not interpret data: %s' % str(col[idx]))
                    return self.return_with_error(retval)
                
            retval[data['AXIS']].append(data)
        
            
        return retval

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

    def dump_data(self,data):
        '''
        write all data to binary data file
        '''
        for axis in ['AZ','EL']:
            npts = len(data[axis])
            rec = np.recarray(names=rec_names,formats="uint8,float64,float64",shape=(npts))
            for idx in range(npts):
                rec[idx].STX = 0xAA
                rec[idx].TIMESTAMP = data[axis][idx]['TIMESTAMP']
                rec.VALUE = data[axis][idx]['ACT_POSITION']

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

        errmsg = []
        errlevel = 0
        retval['TIMESTAMP'] = ans['TIMESTAMP']
        retval['data'] = ans
        if len(ans['AZ'])==0:
            errmsg.append('no azimuth data')
            errlevel += 1
        else:
            retval['AZ'] = ans['AZ'][-1]['ACT_POSITION']
            retval['AZ TIMESTAMP'] = ans['AZ'][-1]['TIMESTAMP']


        if len(ans['EL'])==0:
            errmsg.append('no elevation data')
            errlevel += 1
        else:                        
            retval['EL'] = ans['EL'][-1]['ACT_POSITION'] + self.el_zero_offset
            retval['EL TIMESTAMP'] = ans['EL'][-1]['TIMESTAMP']

        if errlevel >= 2:
            retval['error'] = '\n'.join(errmsg)
            return self.return_with_error(retval)        

        if dump:
            try:
                dump_ok = self.dump_data(ans)
            except:
                retval['error'] = make_errmsg('Could not dump data to file')
                return self.return_with_error(retval)            
            
        return retval

    def show_azel(self):
        '''
        print the azimuth and elevation to screen
        '''
        ans = self.get_azel()
        if not ans['ok']:
            print('AZ,EL = ERROR: %s' % ans['error'])
            return

        print('AZ,EL = %.3f %.3f' % (ans['AZ'],ans['EL']))
        return


    def get_position():
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
        '''
        return self.send_command('AZ %f' % az)

    def goto_el(self,el):
        '''
        send command to move to the given elevation
        we correct for the elevation offset
        '''
        cmd_el = el - self.el_zero_offset
        return self.send_command('EL %f' % cmd_el)

    
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

        self.goto_az(self.azmin)
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
                self.goto_el(elmax)
                time.sleep(1) # wait before next command
                elok = self.wait_for_arrival(el=elmax)
                if not elok:
                    print('ERROR! Did not successfully get to starting elevation position')
                    return False
            

                self.goto_el(elmin)
                azok = self.wait_for_arrival(el=elmin)
                if not azok:
                    print('ERROR! Did not successfully get to starting azimuth position')
                    return False

                az += azstep
                self.goto_az(az)
                self.wait_for_arrival(az=az)

            azstep = -azstep

        return True
    
