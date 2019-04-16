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

from qubichk.copy_data import copy2central, central_datadir, calsource2fits

copy2central()

os.chdir(central_datadir)

glob_pattern = 'calsource_????????T??????.dat'
datfiles = glob(glob_pattern)
datfiles.sort()
for f in datfiles:
    rootname = f.replace('.dat','')
    fitsname = rootname+'.fits'
    if not os.path.isfile(fitsname):
        calsource2fits(f)

        
