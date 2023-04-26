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

The data obtained after the subscribe method will be:

TIMESTAMP : AXIS : ACT_VELOCITY : TARGET_VELOCITY : ACT_POSITION : TARGET_POSITION : ACT_TORQUE : IS_READY : IS_HOMED

example:
1682446097.96:AZ:0:0:1.0101177366738976:0.0:False:1:1

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

IS_READY: this is a bit from the StatusWord of the KEB driver and
          means that it is ready for operation (no exception was
          raised)......maybe this is too obvious.

IS_HOMED: this is a boolean variable from the program and not from the
          StatusWord. The server app has no memory and the
          HomingRoutine should be executed every time the system is
          restarted. This decision was committed thinking about system
          security.

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

'''
import socket,time
import datetime as dt

class obsmount:
    '''
    class to read to and command the observation mount
    '''
    
    mount_ip = '192.168.2.103'
    listen_port = 4546
    command_port = 4545
    el_zero_offset = 50 - 17.952062612098484
    datefmt = '%Y-%m-%d-%H:%M:%S UT'
    data_keys = 'TIMESTAMP:AXIS:ACT_VELOCITY:TARGET_VELOCITY:ACT_POSITION:TARGET_POSITION:ACT_TORQUE:IS_READY:IS_HOMED'.split(':')
    available_commands = ['AZ','EL','DOHOMING','STOP','ABORT']
    wait = 0.0 # seconds to wait before next socket command
    verbosity = 0
    testmode = False
    
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
                      

    def init_socket(self,port='data'):
        '''
        initialize the communication socket
        the port is either 'data' or 'command'
        '''
        retval = {}
        retval['ok'] = True
        if port=='data':
            port_num = self.listen_port
            socktype = socket.SOCK_DGRAM
        else:
            port_num = self.command_port
            socktype = socket.SOCK_STREAM

        self.printmsg('creating socket with type: %s' % socktype)
        self.sock[port] = socket.socket(socket.AF_INET, socktype)
        self.sock[port].settimeout(1)
        try:
            self.printmsg('connecting to address: %s:%i' % (self.mount_ip,port_num))
            self.sock[port].connect((self.mount_ip,port_num))
            time.sleep(self.wait)
            self.printmsg('sending OK')
            ans = self.sock[port].send('OK'.encode())
            self.printmsg('return from socket.send: %s' % ans)
            self.subscribed[port] = True
            self.error = None
        except socket.timeout:
            self.subscribed[port] = False
            self.error = 'TIMEOUT'
        except:
            self.subscribed[port] = False
            self.error = 'SOCKET ERROR'

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

    def read_data(self):
        '''
        once we're subscribed, we can listen for the data
        '''
        port = 'data'
        retval = {}
        retval['ok'] = True
        retval['error'] = 'NONE'

        # check that we are subscribed
        if not self.subscribed[port]:
            self.subscribe(port='data')

        if not self.subscribed[port]:
            retval['error'] = 'could not subscribe'
            return self.return_with_error(retval)

        lines = []
        try:
            for idx in range(2):
                time.sleep(self.wait)
                dat = self.sock[port].recv(128)
                lines.append(dat.decode())
                self.printmsg('[%i] %s' % (idx,lines[-1]))
        except:
            retval['error'] = 'could not get az,el data'
            self.subscribed[port] = False
            self.return_with_error(retval)

        for line in lines:
            col = line.split(':')
            if len(col)!=len(self.data_keys):
                retval['error'] = 'inappropriate data length'
                return return_with_error(retval)
                            
            data = {}
            for idx,key in enumerate(self.data_keys):
                if key=='AXIS':
                    data[key] = col[idx]

                elif key=='IS_READY':
                    tf_str = col[idx]
                    if tf_str=='False':
                        data[key] = False
                    else:
                        data[key] = True
                else:
    
                    try:
                        data[key] = eval(col[idx])
                    except:
                        retval['error'] = 'could not interpret data: %s' % col[idx]
                        retval['data'] = data
                        return self.return_with_error(retval)
                
            retval[data['AXIS']] = data
            
        return retval

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
            retval['error'] = 'command unsuccessful'
            self.subscribed[port] = False
            self.return_with_error(retval)

        return retval


    def get_azel(self):
        '''
        get the azimuth and elevation and return it with a timestamp
        '''
        retval = {}
        retval['ok'] = True
        retval['error'] = 'NONE'

        ans = self.read_data()
        if not ans['ok']:
            return self.return_with_error(ans)


        retval['AZ'] = ans['AZ']['ACT_POSITION']
        retval['AZ tstamp'] = ans['AZ']['tstamp']
        retval['EL'] = ans['EL']['ACT_POSITION'] + self.el_zero_offset
        retval['EL tstamp'] = ans['EL']['tstamp']
        retval['tstamp reception'] = dt.datetime.utcnow().timestamp()
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
            

        

        
