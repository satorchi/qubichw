'''
$Id: platform.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed  5 Jun 15:54:28 CEST 2019
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

help: https://docs.python.org/2/howto/sockets.html

list of commands in the manuel:  TrioBASIC Commands (Chapter 2).pdf

get info from the QUBIC lab platform (the red LAL platform)

'''
import socket,time
import datetime as dt

broadcast_port = 23 # telnet port
platform_ip = '192.168.2.250'
platform_outfile = 'platform.dat'


def send_command(cmd):
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.connect((platform_ip,broadcast_port))
    except socket.timeout:
        return 'TIMEOUT'
    except:
        return 'SOCKET ERROR'
    
    encoded_cmd = (cmd+'\r\n').encode()
    sock.send(encoded_cmd)

    reply = sock.recv(8192)
    reply_decoded = reply.decode()
    sock.close()
    return reply_decoded


def get_encoder_position(debug=False):
    reply = send_command('BASE(0)')
    reply = send_command('PRINT MPOS')
    lines =  reply.split('\n')
    if len(lines)>=2:
        az = lines[1].strip()
    else:
        az = 'bad answer'
    if debug:print(reply)
        
    reply = send_command('BASE(1)')
    reply = send_command('PRINT MPOS')
    lines = reply.split('\n')
    if len(lines)>=2:
        el = lines[1].strip()
    else:
        el = 'bad answer'
    if debug:print(reply)
    return az,el

def get_position():
    azwarn = False
    elwarn = False
    enc_az,enc_el = get_encoder_position()
    if enc_az==enc_el: azwarn = True
    try:
        az = (float(enc_az)-32768) * (360/65536)
    except:
        az = 'bad answer'
        azwarn = True

    try:
        el = (float(enc_el)-32768) * (360/65536) + 124.35
        if el>360: el -= 360
    except:
        el = 'bad answer'
        elwarn = True
    return az,el,azwarn,elwarn

def get_mac():
    reply = send_command('PRINT IP_MAC')
    mac_no = int(reply.split('\n')[1].strip())
    hex_str = '%012x' % mac_no
    hex_list = []
    for idx in range(6):
        n1 = 2*idx
        n2 = n1 + 2
        hex_list.append(hex_str[n1:n2])
    mac_str = ':'.join(hex_list)
    return mac_str

def get_ip():
    reply = send_command('ETHERNET(0,-1,0)')
    ip = reply.split('\n')[1].strip()
    return ip

def reset_ip_hk():
    reply = send_command('IP_ADDRESS = 192.168.2.250')
    reply = send_command('IP_GATEWAY = 192.168.2.1')
    reply = send_command('IP_NETMASK = 255.255.255.0')
    reply = send_command('EX(1)')
    return

def reset_ip_default():
    reply = send_command('IP_ADDRESS = 192.168.0.250')
    reply = send_command('IP_GATEWAY = 192.168.0.1')
    reply = send_command('IP_NETMASK = 255.255.255.0')
    reply = send_command('EX(1)')
    return

def write_positions():
        az,el = get_position()
        now_str = dt.datetime.utcnow().strftime('%s.%f')
        h = open(platform_outfile,'a')
        msg = '%s %s %s' % (now_str,az,el)
        h.write(msg+'\n')
        h.close()
        return
    

def monitor_positions():
    while True:
        write_positions()
        time.sleep(0.2)




