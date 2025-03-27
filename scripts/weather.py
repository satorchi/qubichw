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
import sys,re,time,os
import datetime as dt
from urllib.request import urlopen
from qubichk.utilities import shellcommand

server0 = '45.224.140.42:8989'
server1 = '192.168.88.98'
server2 = '192.168.88.13' # inside weather 2025-03-27 19:53:16
server3 = '192.168.88.14'
server4 = '192.168.88.20'
server5 = '192.168.88.18' # inside weather 2025-03-26 15:50:23, now outside (see above)
inside_server = server2
def parseargs(argv):
    '''
    parse the command line arguments
    '''
    options = {}
    options['log'] = False  # log result
    options['logfile'] = '/home/qubic/data/temperature/broadcast/weather.txt'
    options['period'] = None # sampling period in seconds (if None, print once and exit)
    options['server'] = None
    options['username'] = 'wstation01'
    options['verbosity'] = 0

    for arg in argv:
        if arg=='--log':
            options['log'] = True
            continue

        if arg.find('--logfile=')==0:
            options['logfile'] = arg.split('=')[1]
            continue

        if arg=='--quiet':
            options['verbosity'] = 0
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

        if arg.find('--user=')==0:
            options['username'] = arg.split('=')[1]
            continue
        
        if arg.find('--verbosity=')==0:
            options['verbosity'] = eval(arg.split('=')[1])
            continue

    if options['server'] is None:
        options['server'] = choose_server()
        
    return options

def choose_server():
    '''
    decided whether we can use the internal network, or the internet
    '''
    
    ip = None
    cmd = '/sbin/ip address show dev eth2'
    out,err = shellcommand(cmd)
    for line in out.split('\n'):
        col = line.strip().split()
        if col[0]=='inet':
            ip = col[1].split('/')[0]
            break
        
    if ip is None: return server0
    if ip.find('192.168.88.')==0: return server4
    if ip.find('192.168.2.')==0: return server4
    return server0

def get_weather(options):
    '''
    get the measurements from the webpage
    '''
    if options['verbosity']>1:
        print('getting weather conditions from server: %s' % options['server'])
    
    if options['server']==inside_server: return get_inside_weather(options)

    return get_outside_weather(options)

def get_weather_html(options):
    '''
    get the measurements from the weather station outside the dome running an html server
    '''

    url = 'http://%s/index.asp' % options['server']
    values = {}
    values['ok'] = False
    values['temperature'] = None
    values['humidity'] = None
    values['message'] = 'No info'

    try:
        website = urlopen(url,timeout=5)
        pg = website.read()
    except:
        if options['verbosity']>0: print('could not get weather info from %s' % url)
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

    
def read_weather_csv(weather_file):
    '''
    read the CSV file from the weather station
    '''
    weather_keys = ['date','temperature','humidity','battery','pressure','windspeed','winddir','radiation','rain']
    utoffset = dt.timedelta(hours=3) # weather station data is in ART
    
    if not os.path.isfile(weather_file):
        print('weather file not found: %s' % weather_file)
        return None

    
    h = open(weather_file)
    lines = h.read().split('\n')
    h.close()
    del(lines[-1])

    weather_data = {}
    for key in weather_keys:
        weather_data[key] = []

    for line in lines:
        col = line.split(',')
        for idx,key in enumerate(weather_keys):
            if key=='date':
                weather_data[key].append(dt.datetime.strptime(col[0],'%H:%M:%S %d-%m-%Y') + utoffset)
                continue
            weather_data[key].append(eval(col[idx]))

    weather_data['ok'] = True
    weather_data['message'] = 'data read from %s' % weather_file
    return weather_data


def get_weather_csv(options):
    '''
    get the weather measurements from the CSV file on the weather station server
    '''
    values = {}
    values['ok'] = False
    values['temperature'] = None
    values['humidity'] = None
    values['message'] = 'No info'

    if options['server'] is None:
        server = choose_server()
    else:
        server = options['server']

    username = options['username']
    weather_data_dir = 'TECMES/data'
    out,err = shellcommand('ssh %s@%s "ls -t %s/????????.csv"' % (username,server,weather_data_dir))
    csvfile_fullpath = out.split('\n')[0]
    csvfile = os.path.basename(csvfile_fullpath)
    out,err = shellcommand('scp -p %s@%s:%s .' % (username,server,csvfile_fullpath))

    weather_data = read_weather_csv(csvfile)
    if weather_data is None:
        return values

    for key in ['ok','message']:
        values[key] = weather_data[key]

    for key in ['date','temperature','humidity']:
        values[key] = weather_data[key][-1]
    

    return values

def get_outside_weather(options):
    '''
    get the measurements from the weather station outside the dome
    '''

    if options['verbosity']>1:
        print('getting outside weather conditions')
    
    return get_weather_csv(options)


def get_inside_weather(options):
    '''
    get the measurements from the weather station inside the dome
    '''
        
    url = 'http://%s/index.html' % options['server']
    if options['verbosity']>1:
        print('getting inside weather conditions from: %s' % url)

    
    values = {}
    values['ok'] = False
    values['temperature'] = None
    values['humidity'] = None
    values['message'] = 'No info'

    try:
        website = urlopen(url,timeout=15)
        pg = website.read()
    except:
        if options['verbosity']>0:
            print('could not get weather info from %s' % url)
        return values

    if options['verbosity']>1:
        print('vvvvvv webpage vvvvvv\n%s\n^^^^^^ webpage ^^^^^^' % pg.decode())
        
    reslist = []
    srchpattern = ['^Humidity (\(.*\)) .*:(.*)$','^Temperature (\(.*\)) .*:(.*)$']
    for idx,line in enumerate(pg.decode().split('\n')):
        for pattern in srchpattern:
            m = re.search(pattern,line)
            if not m: continue

            valstr = m.groups()[1]
            try: 
                val = eval(valstr)
            except:
                continue

            units = m.groups()[0].replace('(','').replace(')','')
                
            reslist.append('%.2f %s' % (val,units))
            if units.find('C')>=0:
                values['temperature'] = val
            if units.find('%')>=0:
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

    if 'date' in values.keys():
        tstamp = values['date'].timestamp()
    else:
        tstamp = dt.datetime.utcnow().timestamp()
    line = '%f %f %f\n' % (tstamp,values['temperature'],values['humidity'])
    if options['log']:
        h = open(options['logfile'],'a')
        h.write(line)
        h.close()

    if options['verbosity']>0:
        print(line)
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
