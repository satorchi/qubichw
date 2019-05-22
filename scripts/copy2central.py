#!/usr/bin/env python
'''
$Id: copy2central.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Tue 16 Apr 2019 07:34:29 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

copy data files to the archive on qubic-central
and convert calsource dat files to fits
'''
from __future__ import division, print_function
import os
from glob import glob
import datetime as dt

from qubichk.copy_data import copy2central, central_datadir, calsource2fits

copy2central()

os.chdir('%s/calsource' % central_datadir)

glob_pattern = 'calsource_????????T??????.dat'
datfiles = glob(glob_pattern)
datfiles.sort()
for f in datfiles:
    h = open(f,'r')
    l1 = h.readline()
    h.close()
    try:
        tstamp = float(l1.strip().split()[0])
        fitsname = 'calsource_%s.fits' % dt.datetime.utcfromtimestamp(tstamp).strftime('%Y%m%dT%H%M%S')
    except:
        rootname = f.replace('.dat','')
        fitsname = rootname+'.fits'

    print('expected output FITS file: %s' % fitsname)
    if not os.path.isfile(fitsname):
        calsource2fits(f)
    else:
        print('file exists, not overwriting: %s' % fitsname)

        

        
