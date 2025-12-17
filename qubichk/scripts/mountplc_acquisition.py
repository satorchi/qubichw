#!/usr/bin/env python3
'''
$Id: mountplc_acquisition.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 01 Dec 2025 12:04:09 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

read mount position data from the PLC and dump it to binary data file
'''
import sys,os
from qubichk.obsmount import obsmount
from qubichk.utilities import make_errmsg, verify_directory
from satorchipy.datefunctions import utcnow

dump_dir = None

if len(sys.argv)>1:
    for arg in sys.argv[1:]:
        dump_dir = verify_directory(arg)

date_str = utcnow().strftime('%Y-%m-%d %H:%M:%S UT')
if dump_dir is None:
    msg = 'not dumping Az/El data'
else:
    msg = 'dumping to directory: %s' % dump_dir
print('%s | %s' % (date_str,msg))

mount = obsmount()
mount.acquisition(dump_dir=dump_dir)

            
