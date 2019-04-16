#!/usr/bin/env python
'''
$Id: copy2central.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Tue 16 Apr 2019 19:09:06 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

convert calsource dat file to fits
'''
from __future__ import division, print_function
import os,sys

from qubichk.copy_data import calsource2fits

if len(sys.argv)<2:
    print('usage: calsource2fits.py <filename>')
    quit()

f = sys.argv[1]
if not os.path.isfile(f):
    print('file not found: %s' % f)
    quit()
    
rootname = f.replace('.dat','')
fitsname = rootname+'.fits'
if os.path.isfile(fitsname):
    print('file already exists.  not overwriting %s' % fitsname)
    quit()
    
calsource2fits(f)

        
