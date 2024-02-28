#!/usr/bin/env python3
'''
$Id: weather.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Fri 11 Nov 2022 11:59:12 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

read the weather stuff from the weather station online
'''
import sys,re,time
import datetime as dt
from urllib.request import urlopen
from qubichk.utilities import shellcommand

def parseargs(argv):
    '''
    parse the command line arguments
    '''
    options = {}
    options['log'] = False  # log result
    options['logfile'] = '/home/qubic/data/temperature/broadcast/weather.txt'
    options['print'] = True # print result to screen
    options['period'] = None # sampling period in seconds (if None, print once and exit)
    options['server'] = None

    for arg in argv:
        if arg=='--log':
            options['log'] = True
            continue

        if arg.find('--logfile=')==0:
            options['logfile'] = arg.split('=')[1]
            continue

        if arg=='--quiet':
            options['print'] = False
            continue

        if arg.find('--period=')==0:
            try:
                period = eval(arg.split('=')[1])
                options['period'] = period
            except:
                continue

        if arg.find('--server=')==0:
            options['server'] = arg.split('=')[1]
            continue

    if options['server'] is None:
        options['server'] = choose_server()
        
    return options

def choose_server():
    '''
    decided whether we can use the internal network, or the internet
    '''
    server0 = '45.224.140.42:8989'
    server1 = '192.168.88.98'
    server2 = '192.168.88.47'
    
    ip = None
    cmd = '/sbin/ip address show dev eth0'
    out,err = shellcommand(cmd)
    for line in out.split('\n'):
        col = line.strip().split()
        if col[0]=='inet':
            ip = col[1].split('/')[0]
            break
        
    if ip is None: return server0
    if ip.find('192.168.88.')==0: return server1
    if ip.find('192.168.2.')==0: return server1
    return server0

def get_weather(options):
    '''
    get the measurements from the webpage
    '''
    url = 'http://%s/index.asp' % options['server']
    values = {}
    values['ok'] = False
    values['temperature'] = None
    values['humidity'] = None
    values['message'] = None

    try:
        website = urlopen(url,timeout=5)
        pg = website.read()
    except:
        return values

    reslist = []
    for idx,line in enumerate(pg.decode().split()):
        m = re.search('s21.',line)
        if m:
            col = line.split('>')
            valstr = col[1].split('&')[0]
            try: 
                val = eval(valstr)
            except:
                continue
            
            units = col[1].split('&nbsp;')[-1].split('<')[0]
            reslist.append('%.2f %s' % (val,units))
            if units.find('C')>=0:
                values['temperature'] = val
            if units.find('RH')>=0:
                values['humidity'] = val


    msg = ' '.join(reslist)
    values['message'] = msg
    values['ok'] = True
    return values

def show_weather(values,options):
    '''
    log the weather and/or show it on screen
    '''
    if not values['ok']: return
    
    tstamp = dt.datetime.utcnow().timestamp()
    if options['log']:
        line = '%f %f %f\n' % (tstamp,values['temperature'],values['humidity'])
        h = open(options['logfile'],'a')
        h.write(line)
        h.close()

    if options['print']:
        print(values['message'])

    return


# main program starts here
if __name__=='__main__':

    options = parseargs(sys.argv)
    
    if options['period'] is not None:

        while True:
        
            values = get_weather(options)
            show_weather(values,options)
            time.sleep(options['period'])

    else:
        
        values = get_weather(options)
        show_weather(values,options)
