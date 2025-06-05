#!/usr/bin/env python3
'''
$Id: goto_pos.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 05 Jun 2025 18:53:30 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

command the obsmount to the given elevation
'''
import sys
from qubichk.obsmount import obsmount

# parse arguments
ignore_limit = False
pos = None
max_limit = None
min_limit = None
azel = None
for idx,arg in enumerate(sys.argv):
    if idx==0: continue
    try:
        pos = eval(arg)
    except:
        pass

    if arg.lower().find('ignore-limit')>=0:
        ignore_limit = True
        continue

    if arg.lower().find('el')>=0:
        azel = 'el'
        continue

    if arg.lower().find('az')>=0:
        azel = 'az'
        continue
    
    
if azel is None:
    print('Please specify either azimuth or elevation')
    quit()

if azel=='el':    
    azel_str = 'elevation'
    max_limit = obsmount.elmax
    min_limit = obsmount.elmin
else:
    azel_str = 'azimuth'
    max_limit = obsmount.azmax
    min_limit = obsmount.azmin
    
if pos is None:
    print('Please enter a valid %s angle!' % azel_str)
    quit()

if pos>max_limit or pos<min_limit:
    if not ignore_limit:
        print('%s angle is out of range!' % azel_str)
        quit()

    print('WARNING! Sending %s command beyond acceptable range!' % azel_str)
    
    
    
mount = obsmount()
if azel=='el':
    mount.goto_el(pos)
    mount.wait_for_arrival(el=pos)
else:
    mount.goto_az(pos)
    mount.wait_for_arrival(az=pos)

