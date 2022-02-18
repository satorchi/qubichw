#!/usr/bin/env python3
'''
$Id: show_position.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Fri 18 Feb 2022 13:21:47 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

show the position of the platform
'''
import datetime as dt
from qubichk.platform import get_position

header = '%s   %s   %s' % ('time'.center(20),'az'.center(5),'el'.center(5))
print(header,end='\n')

while True:
    az,el = get_position()
    date_str = dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    if type(az)==str:
        az_str = 'ERROR'.center(7)
    else:
        az_str = '%7.2f' % az
    if type(el)==str:
        el_str = 'ERROR'.center(7)
    else:
        el_str = '%7.2f' % el
    
    line = '%s   %s   %s' % (date_str,az_str,el_str)
    print(line,end='\r')

    
