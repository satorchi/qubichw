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

DATA : AXES : ACT_VELOCITY : TARGET_VELOCITY : ACT_POSITION : TARGET_POSITION : ACT_TORQUE : IS_READY : IS_HOMED

DATA: constant string

AXES: AZ or EL

ACT_VELOCITY: actual velocity (this is the actual value that KEB
              driver calculates)

TARGET_VELOCITY: target velocity that will be using while motor is
                 running

ACT_POSITION: actual position. This value is already converted via a
              calibration constant and should be a float. 0 means that
              the axis is near the lower limit switch and will be
              touching the homing switch (not yet activating it).

TARGET_POSITION: the last target position that was written into the
                 KEB driver.

IS_READY: this is a bit from the StatusWord of the KEB driver and
          means that it is ready for operation (no exception was
          raised)......maybe this is too obvious.

IS_HOMED: this is a boolean variable from the program and not from the
          StatusWord. The server app has no memory and the
          HomingRoutine should be executed every time the system is
          restarted. This decision was committed thinking about system
          security.

In order to subscribe to the update service you should send the "OK" message to
the RPi to the 4546 port. After that you will start receiving messages with the
above structure every 100ms.

The IP for the rpi running the server is 192.168.2.103.  4545 is
listening for commands but 4546 is listening for incoming subscribers.

'''
import socket,time

class obsmount:
    '''
    class to read to and command the observation mount
    '''
    
    mount_ip = '192.168.2.103'
    subscribe_port = 4546
    listen_port = 4545
    
    def __init__(self):
        '''
        so far, initialization is done manually
        '''
        self.subscribed = False
        return

    def init_socket(self,port='subscribe'):
        '''
        initialize the communication socket
        '''
        if port=='subscribe':
            port_num = self.subscribe_port
        else:
            port_num = self.listen_port
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(1)
        try:
            self.sock.connect((self.mount_ip,port_num))
            time.sleep(1)
            self.subscribed = True
            self.error = None
        except socket.timeout:
            self.subscribed = False
            self.error = 'TIMEOUT'
            print('ERROR: could communicate because of %s to %s:%s' % (self.error,self.mount_ip,port_num))
            return None
        except:
            self.subscribed = False
            self.error = 'SOCKET ERROR'
            print('ERROR: could communicate because of %s to %s:%s' % (self.error,self.mount_ip,port_num))
            return None

        return True

    
    def subscribe(self):
        '''
        subscribe to the observation mount server
        '''

        if not self.subscribed:
            self.init_socket(port='subscribe')
        
        # check that the socket is valid
        if not self.subscribed:
            print('ERROR: could not subscribe')
            return None

        # subscribe
        encoded_cmd = ('OK\r\n').encode()
        try:
            self.sock.send(encoded_cmd)
            time.sleep(1)
        except socket.timeout:
            self.subscribed = False
            self.error = 'TIMEOUT'
            return None
        except:
            self.subscribed = False
            self.error = 'SOCKET ERROR'
            return None
            
        return self.subscribed

    def read_data(self):
        '''
        once we're subscribed, we can just listen for the data
        '''

        # check that we are subscribed
        if not self.subscribed:
            self.subscribe()

        if not self.subscribed:
            print('ERROR: could not subscribe')
            return None

        port = self.listen_port

        # check that the socket is valid
        if not self.init_socket(port='listen'):
            print('ERROR: could not establish connection to data server')
            return None

        ans = self.sock.recv(8192)
        lines = ans.decode().split()

        # temporary
        print('\n'.join(lines))
        return lines

    
