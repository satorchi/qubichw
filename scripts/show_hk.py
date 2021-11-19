#!/usr/bin/env python3
'''
$Id: show_hk.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 18 Nov 2021 13:13:45 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

show the latest housekeeping values on screen
'''
import sys,os
from glob import glob
import datetime as dt

hk_dir = '/home/qubic/data/temperature/broadcast'
if not os.path.isdir(hk_dir):
    hk_dir = '/home/steve/data/2021/hk'

if not os.path.isdir(hk_dir):
    print('could not find Housekeeping data directory')
    quit()
    
exclude_files = ['TEMPERATURE_RAW.txt',
                 'TEMPERATURE_VOLT.txt',
                 'LABELS.txt',
                 'compressor1_log.txt',
                 'compressor2_log.txt']

def read_labels():
    '''
    read the sensor labels
    '''
    labels = {}
    
    labelfile = hk_dir+os.sep+'LABELS.txt'
    if os.path.isfile(labelfile):
        h = open(labelfile,'r')
        lines = h.read().split('\n')
        del(lines[-1])
        for line in lines:
            col = line.split('=')
            if len(col)<2: continue
            key = col[0].strip()
            val = col[1].strip()
            labels[key] = val
        h.close()

    heaterfile = os.environ['HOME']+os.sep+'powersupply.conf'
    if not os.path.isfile(heaterfile): return labels

    h = open(heaterfile,'r')
    lines = h.read().split('\n')
    del(lines[-1])
    for line in lines:
        col = line.split(':')
        if len(col)<2: continue
        key = col[0].strip()
        val = col[1].strip()
        labels[key] = val
    h.close()
    return labels
    
def read_lastline(filename):
    '''
    read the last line of a file
    '''
    
    if not os.path.isfile(filename):
        print('File not found: %s' % filename)
        return None

    h = open(filename,'r')
    nbytes = h.seek(0,os.SEEK_END)
    near_end = nbytes - 4096
    if near_end<0: near_end=0
    h.seek(near_end,0)
    lines = h.read().split('\n')
    h.close()
    if len(lines)<2:
        lastline = lines[0]
    else:
        lastline = lines[-2]

    col = lastline.split()
    if len(col)<2:
        print('Unexpected string: %s' % lastline)
        return None

    tstamp = float(col[0])
    val = float(col[1])
    return tstamp, val


labels = read_labels()

hk_files = glob(hk_dir+os.sep+'*.txt')
hk_files.sort()
lines = []
for F in hk_files:
    basename = os.path.basename(F)
    
    if basename in exclude_files: continue

    retval = read_lastline(F)
    if retval is None: continue

    label = ''
    labelkey = basename.replace('.txt','')
    if labelkey in labels.keys():
        label = labels[labelkey]

    units = None
    if basename=='AVS47_1_ch0.txt':
        units = 'Ohm'
    elif basename.find('TEMPERATURE')==0 or basename.find('AVS')==0:
        units = 'K'
    elif basename.find('PRESSURE')==0:
        units = 'mbar'
    elif basename.find('Volt')>0:
        units = 'V'
    elif basename.find('Amp')>0:
        units = 'A'
    elif basename.find('MHS')==0:
        units = 'steps'
    else:
        units = ''
        
        
    tstamp,val = retval


    date = dt.datetime.utcfromtimestamp(tstamp)
    date_str = date.strftime('%Y-%m-%d %H:%M:%S')

    val_str = None
    
    if abs(val)>1:
        val_str = '%7.3f %s' % (val,units)
    else:
        val_str = '%7.3f m%s' % (val*1000,units)

    if units == 'mbar':
        val_str = '%12.5e %s' % (val,units)
        
    if units == 'steps':
        val_str = '%i %s' % (int(val), units)

    if val_str is None:
        val_str = '%12.5e %s' % (val,units)

    line = '%s %20s %20s %s' % (date_str, val_str, label, labelkey)
    lines.append(line)

page = '\n'.join(lines)
print(page)


