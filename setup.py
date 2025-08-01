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

def shellcommand(cmd):
    '''
    run a shell command
    '''    
    proc = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out,err = proc.communicate()
    return out.decode().strip(),err.decode().strip()


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
      packages=['qubichw','qubichk','pystudio'],
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
        out,err = shellcommand(cmd)
    tmp_file = 'qubicpack_installation_temporary_file_%s.txt' % dt.datetime.now().strftime('%Y%m%dT%H%M%S')
    cmd = 'touch %s/%s' % (exec_dir,tmp_file)
    out,err = shellcommand(cmd)
    if err:
        continue
    else:
        exec_dir_ok = True
        os.remove('%s/%s' % (exec_dir,tmp_file))
        break
    
scripts = ['scripts/calsource_commander.py',
           'scripts/cf_commander.py',
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
           'scripts/start_cf_manager.sh',
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
           'scripts/compressorstatus.py',
           'scripts/compressor1reset',
           'scripts/compressor2reset',
           'scripts/compressor_log.py',
           'scripts/central_command.py',
           'scripts/ups_alarm.py',
           'scripts/ups_log.py',
           'scripts/calsource_on',
           'scripts/calsource_off',
           'scripts/show_hk.py',
           'scripts/show_hk',
           'scripts/show_position.py',
           'scripts/stop_mount.py',
           'scripts/start_apctunnel.sh',
           'scripts/start_cctunnel.sh',
           'scripts/configfile_backup.sh',
           'scripts/test_alarm.py',
           'scripts/copydata',
           'scripts/clean-hk.sh',
           'scripts/mount_entropy.sh',
           'scripts/start_gpsd-ntpd.sh',
           'scripts/weather.py',
           'scripts/start_weather.sh',
           'scripts/mech_openclose.py',
           'scripts/kellypi_on',
           'scripts/kellypi_off',
           'scripts/fpga_on',
           'scripts/fpga_off',
           'scripts/energenie_commander.py',
           'qubichw/read_usbthermometer.py',
           'scripts/start_usbthermometer_acq.sh',
           'scripts/run_gps_acquisition.py',
           'scripts/run_gps_broadcast.py',
           'scripts/start_gps_acquisition.sh',
           'scripts/start_gps_broadcast.sh',
           'scripts/start_ups.sh',
           'scripts/run_MCP9808_acquisition.py',
           'scripts/run_MCP9808_broadcast.py',
           'scripts/start_MCP9808_acquisition.sh',
           'scripts/start_MCP9808_broadcast.sh',
           'scripts/run_heater_manager.py',
           'scripts/start_heater_manager.sh',
           'scripts/do_skydip_sequence.py',
           'scripts/goto_pos.py',
           'scripts/goto_az',
           'scripts/goto_el',
           'scripts/kill_all_fridge_cycles.py',
           'scripts/send_telegram_to_subscribers.py'
           ]
if len(sys.argv)>1 and sys.argv[1]=='install' and exec_dir_ok:
    print('installing executable scripts...')
    for F in scripts:
        basename = os.path.basename(F)
        cmd = 'rm -f %s/%s; cp -puv %s %s;chmod +x %s/%s' % (exec_dir,basename,F,exec_dir,exec_dir,basename)
        out,err = shellcommand(cmd)
        if out:print(out.strip())
        if err:print(err.strip())

