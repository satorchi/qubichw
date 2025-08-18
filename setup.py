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
    
scripts = ['qubichk/scripts/calsource_commander.py',
           'qubichk/scripts/cf_commander.py',
           'qubichk/scripts/calsource_set_frequency.py',
           'qubichk/scripts/calsource_step_frequency.py',
           'qubichk/scripts/run_calibration_source.py',
           'qubichk/powersupply.py',
           'qubichk/scripts/make_hk_fits.py',
           'qubichk/scripts/modulator_commander.py',
           'qubichk/scripts/run_bot.py',
           'qubichk/scripts/run_hkserver.py',
           'qubichk/scripts/archive-data.sh',
           'qubichk/scripts/calsource2fits.py',
           'qubichk/scripts/run_horn_monitor.py',
           'qubichk/scripts/plot_hornswitch.py',
           'qubichk/scripts/calsource_hourly_save.py',
           'qubichw/read_calsource.py',
           'qubichk/scripts/start_calsource_acq.sh',
           'qubichk/scripts/start_calsource_manager.sh',
           'qubichk/scripts/start_cf_manager.sh',
           'qubichk/scripts/start_bot.sh',
           'qubichk/scripts/start_hkserver.sh',
           'qubichk/scripts/mmr_mes1.py',
           'qubichk/scripts/lampon.py',
           'qubichk/scripts/lampoff.py',
           'qubichk/scripts/qubic_poweron',
           'qubichk/scripts/qubic_poweroff',
           'qubichk/scripts/hwpon',
           'qubichk/scripts/hwpoff',
           'qubichk/scripts/hornon',
           'qubichk/scripts/hornoff',
           'qubichk/scripts/thermoson',
           'qubichk/scripts/thermosoff',
           'qubichk/scripts/heaterson',
           'qubichk/scripts/heatersoff',
           'qubichk/scripts/hk_ok.py',
           'qubichk/scripts/compressor_commander.py',
           'qubichk/scripts/compressor1on',
           'qubichk/scripts/compressor1off',
           'qubichk/scripts/compressor2on',
           'qubichk/scripts/compressor2off',
           'qubichk/scripts/compressorstatus',
           'qubichk/scripts/compressor1reset',
           'qubichk/scripts/compressor2reset',
           'qubichk/scripts/compressor_log.py',
           'qubichk/scripts/central_command.py',
           'qubichk/scripts/ups_alarm.py',
           'qubichk/scripts/ups_log.py',
           'qubichk/scripts/calsource_on',
           'qubichk/scripts/calsource_off',
           'qubichk/scripts/show_hk.py',
           'qubichk/scripts/show_hk',
           'qubichk/scripts/show_position.py',
           'qubichk/scripts/stop_mount.py',
           'qubichk/scripts/start_apctunnel.sh',
           'qubichk/scripts/start_cctunnel.sh',
           'qubichk/scripts/configfile_backup.sh',
           'qubichk/scripts/test_alarm.py',
           'qubichk/scripts/copydata',
           'qubichk/scripts/clean-hk.sh',
           'qubichk/scripts/mount_entropy.sh',
           'qubichk/scripts/start_gpsd-ntpd.sh',
           'qubichk/scripts/weather.py',
           'qubichk/scripts/start_weather.sh',
           'qubichk/scripts/mech_openclose.py',
           'qubichk/scripts/kellypi_on',
           'qubichk/scripts/kellypi_off',
           'qubichk/scripts/fpga_on',
           'qubichk/scripts/fpga_off',
           'qubichk/scripts/energenie_commander.py',
           'qubichw/read_usbthermometer.py',
           'qubichk/scripts/start_usbthermometer_acq.sh',
           'qubichk/scripts/run_gps_acquisition.py',
           'qubichk/scripts/run_gps_broadcast.py',
           'qubichk/scripts/start_gps_acquisition.sh',
           'qubichk/scripts/start_gps_broadcast.sh',
           'qubichk/scripts/start_ups.sh',
           'qubichk/scripts/run_MCP9808_acquisition.py',
           'qubichk/scripts/run_MCP9808_broadcast.py',
           'qubichk/scripts/start_MCP9808_acquisition.sh',
           'qubichk/scripts/start_MCP9808_broadcast.sh',
           'qubichk/scripts/run_heater_manager.py',
           'qubichk/scripts/start_heater_manager.sh',
           'qubichk/scripts/goto_pos.py',
           'qubichk/scripts/goto_az',
           'qubichk/scripts/goto_el',
           'qubichk/scripts/kill_all_fridge_cycles.py',
           'qubichk/scripts/send_telegram_to_subscribers.py',
           'pystudio/scripts/do_skydip_sequence.py',
           'pystudio/scripts/do_IV_sequence.py',
           'pystudio/scripts/do_NEP_sequence.py',
           'pystudio/scripts/do_SQUID_sequence.py',
           'pystudio/scripts/do_init_frontend.py'
           ]
if len(sys.argv)>1 and sys.argv[1]=='install' and exec_dir_ok:
    print('installing executable scripts...')
    for F in scripts:
        basename = os.path.basename(F)
        cmd = 'rm -f %s/%s; cp -puv %s %s;chmod +x %s/%s' % (exec_dir,basename,F,exec_dir,exec_dir,basename)
        out,err = shellcommand(cmd)
        if out:print(out.strip())
        if err:print(err.strip())

