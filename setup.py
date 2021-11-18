#! /usr/bin/env python3
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
import os,sys,subprocess
import datetime as dt
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

# install the executable scripts, if we have permission
exec_dir_list = ['/usr/local/bin']
if 'HOME' in os.environ.keys():
    localbin = os.environ['HOME']+'/.local/bin'
    exec_dir_list.append(localbin)

exec_dir_ok = False
for exec_dir in exec_dir_list:
    if not os.path.isdir(exec_dir):
        cmd = 'mkdir --parents %s' % exec_dir
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out,err=proc.communicate()
    tmp_file = 'qubicpack_installation_temporary_file_%s.txt' % dt.datetime.now().strftime('%Y%m%dT%H%M%S')
    cmd = 'touch %s/%s' % (exec_dir,tmp_file)
    proc=subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out,err=proc.communicate()
    if err:
        continue
    else:
        exec_dir_ok = True
        break
    
scripts = ['scripts/calsource_commander.py',
           'scripts/calsource_set_frequency.py',
           'scripts/calsource_step_frequency.py',
           'scripts/run_calibration_source.py',
           'qubichk/powersupply.py',
           'scripts/make_hk_fits.py',
           'scripts/modulator_commander.py',
           'scripts/run_bot.py',
           'scripts/run_hkserver.py',
           'scripts/archive-data.sh',
           'scripts/calsource2fits.py',
           'scripts/run_horn_monitor.py',
           'scripts/plot_hornswitch.py',
           'scripts/calsource_hourly_save.py',
           'qubichw/read_calsource.py',
           'scripts/start_calsource_acq.sh',
           'scripts/start_calsource_manager.sh',
           'scripts/start_bot.sh',
           'scripts/start_hkserver.sh',
           'scripts/mmr_mes1.py',
           'scripts/lampon.py',
           'scripts/lampoff.py',
           'scripts/qubic_poweron',
           'scripts/qubic_poweroff',
           'scripts/hwpon',
           'scripts/hwpoff',
           'scripts/hornon',
           'scripts/hornoff',
           'scripts/thermoson',
           'scripts/thermosoff',
           'scripts/heaterson',
           'scripts/heatersoff',
           'scripts/hk_ok.py',
           'scripts/compressor_commander.py',
           'scripts/compressor1on',
           'scripts/compressor1off',
           'scripts/compressor2on',
           'scripts/compressor2off',
           'scripts/compressorstatus',
           'scripts/compressor1reset',
           'scripts/compressor2reset',
           'scripts/central_command.py',
           'scripts/ups_alarm.py',
           'scripts/calsource_on',
           'scripts/calsource_off',
           'scripts/show_hk.py',
           'scripts/show_hk']
if len(sys.argv)>1 and sys.argv[1]=='install' and exec_dir_ok:
    print('installing executable scripts...')
    for F in scripts:
        basename = os.path.basename(F)
        cmd = 'rm -f %s/%s; cp -puv %s %s;chmod +x %s/%s' % (exec_dir,basename,F,exec_dir,exec_dir,basename)
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out,err=proc.communicate()
        if out:print(out.decode().strip())
        if err:print(err.decode().strip())

