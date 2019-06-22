#! /usr/bin/env python
'''
$Id: setup.py <qubichw>
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 18 Mar 2019 11:26:55 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

setup.py for qubichw
'''
from __future__ import division, print_function
import os,sys,subprocess
from setuptools import setup

DISTNAME         = 'qubichw'
DESCRIPTION      = 'Utilities for QUBIC hardware control and monitoring'
AUTHOR           = 'Steve Torchinsky'
AUTHOR_EMAIL     = 'satorchi@apc.in2p3.fr'
MAINTAINER       = 'Steve Torchinsky'
MAINTAINER_EMAIL = 'satorchi@apc.in2p3.fr'
URL              = 'https://github.com/satorchi/qubichw'
LICENSE          = 'GPL'
DOWNLOAD_URL     = 'https://github.com/satorchi/qubichw'
VERSION          = '2.0.0'

with open('README.md') as f:
    long_description = f.read()


setup(install_requires=['numpy'],
      name=DISTNAME,
      version=VERSION,
      packages=['qubichw','qubichk'],
      package_data={'qubichw': ['data/*'], 'qubichk': ['data/*']},
      zip_safe=False,
      author=AUTHOR,
      author_email=AUTHOR_EMAIL,
      maintainer=MAINTAINER,
      maintainer_email=MAINTAINER_EMAIL,
      description=DESCRIPTION,
      license=LICENSE,
      url=URL,
      download_url=DOWNLOAD_URL,
      long_description=long_description,
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: GNU General Public License (GPL)',
          'Topic :: Scientific/Engineering'],
)

# install the executable scripts
exec_dir = '/usr/local/bin'
scripts = ['scripts/calsource_commander.py',
           'scripts/calsource_set_frequency.py',
           'scripts/calsource_step_frequency.py',
           'scripts/run_calibration_source.py',
           'qubichk/powersupply.py',
           'scripts/make_hk_fits.py',
           'scripts/modulator_commander.py',
           'scripts/run_bot.py',
           'scripts/run_hkserver.py',
           'scripts/copy2central.py',
           'scripts/copy2cc.py',
           'scripts/copy2jupyter.py',
           'scripts/calsource2fits.py',
           'scripts/run_horn_monitor.py',
           'scripts/plot_hornswitch.py',
           'scripts/calsource_hourly_save.py',
           'scripts/start_calsource_acq.sh',
           'scripts/start_calsource_manager.sh']
if len(sys.argv)>1 and sys.argv[1]=='install':
    print('installing executable scripts...')
    for F in scripts:
        basename = os.path.basename(F)
        cmd = 'rm -f %s/%s; cp -puv %s %s;chmod +x %s/%s' % (exec_dir,basename,F,exec_dir,exec_dir,basename)
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out,err=proc.communicate()
        if out:print(out.strip())
        if err:print(err.strip())

