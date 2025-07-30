'''
$Id: sequence.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 28 Jul 2025 19:55:53 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

basic sequences for running observations
'''
import time
import numpy as np
from satorchipy.datefunctions import utcnow
from qubichk.imacrt import iMACRT
from qubichk.obsmount import obsmount

#####################################
# defaults
default_setting = {}
default_setting['asicNum'] = [1,2] # both ASICs
default_setting['Voffset'] = 5.5 # Volts
default_setting['amplitude'] = 7.0 # Volts
default_setting['undersampling'] = 1000
default_setting['increment'] = 1
default_setting['duration'] = 120 # seconds
default_setting['elmin'] = 50 # minimum permitted elevation
default_setting['elmax'] = 70 # maximum permitted elevation
default_setting['azmin'] = 0  # minimum permitted azimuth
default_setting['azmax'] = 25 # maximum permitted azimuth (changed to 25 on 2025-06-06 15:51:25 UT)
default_setting['azstep'] = 5 # default step size for azimuth movement for skydips

def set_bath_temperature(self,Tbath,timeout=30,precision=0.003):
    '''
    set the iMACRT PID for the desired temperature and wait until it reaches the temperature
    '''
    # get current temperature
    mgc = iMACRT(device='mgc')
    Tmeas = mgc.get_mgc_measurement()
    if Tmeas=='':
        print('Could not get temperature from MGC3.')
    else:
        print('Tbath is currently: %.3f mK' % (Tmeas*1000))

    
    ans = mgc.set_mgc_setpoint(Tbath)
    if ans is None:
        print('ERROR!  Could not set bath temperature: %.3f K' % Tbath)
        return None
    time.sleep(0.2)
    ans = mgc.set_mgc_pid(1)

    # wait for temperature
    Tdelta = np.abs(Tmeas-Tbath)
    maxcount = int(timeout) + 1
    count = 0
    while (Tdelta>precision) and (count<maxcount):
        time.sleep(1)
        Tmeas = mgc.get_mgc_measurement()
        Tdelta = np.abs(Tmeas-Tbath)
        count += 1
    mgc.disconnect()
    
    if Tdelta>precision:
        print('Did not reach desired bath temperature.  Current temperature: %.3f mK' % (1000*Tmeas))
        return False

    print('Current bath temperature: %.3f mK' % (1000*Tmeas))
    return True

    

def do_IV_measurement(self,
                      asicNum=None,
                      Voffset=None,
                      amplitude=None,
                      undersampling=None,
                      increment=None,
                      Tbath=None,
                      duration=None,
                      comment=None):
    '''
    run the sequence to measure the I-V curve
    '''

    #####################################
    # defaults
    if asicNum is None: asicNum = default_setting['asicNum']
    if Voffset is None: Voffset = default_setting['Voffset']
    if amplitude is None: amplitude = default_setting['amplitude']
    if undersampling is None: undersampling = default_setting['undersampling']
    if increment is None: increment = default_setting['increment']
    if duration is None: duration = default_setting['duration']
    if comment is None: comment = 'I-V measurement sent by pystudio'


    #####################################
    # make sure the bias does not go out of acceptable range
    Vmax = Voffset + 0.5*amplitude
    if (Vmax>9):
        print('STOP:  Maximum bias voltage will be greater than 9 Volts: %.2f V' % Vmax)
        return None

    Vmin = Voffset - 0.5*amplitude
    if (Vmin<1.0):
        print('STOP:  Minimum bias voltage will be less than 1 Volt: %.2f V' % Vmin)
        return None

    #####################################
    # check for desired bath temperature
    if Tbath is None:
        print('Doing I-V curves at current temperature:  No commands will be sent to iMACRT')
        Tbath_ok = True
    else:
        Tbath_ok = self.set_bath_temperature(Tbath)

    if not Tbath_ok:
        print("Tbath temperature not reached.  I'm not continuing with the I-V curve measurement.")
        return None


    #####################################
    # configure the bolometers

    # stop all regulations
    ack = self.send_stopFLL(asicNum)

    # configure sine curve bias
    ack = self.send_TESDAC_SINUS(asicNum,amplitude,Voffset,undersampling,increment)

    # start all regulations
    ack = self.send_startFLL(asicNum)

    # start recording data
    # get current temperature
    mgc = iMACRT(device='mgc')
    Tmeas = mgc.get_mgc_measurement()
    mgc.disconnect()
    if Tmeas=='':
        dataset_name = 'IV'
    else:
        dataset_name = 'IV_.0fmK' % (1000*Tmeas)
    ack = self.send_startAcquisition(dataset_name,comment)

    # wait for measurement
    time.sleep(duration)

    # stop the acquisition
    ack = self.send_stopAcquisition()

    print('%s - IV measurement completed' % utcnow().strftime('%Y-%m-%d %H:%M:%S'))
    return

def do_NEP_measurement(self,
                       asicNum=None,
                       Voffset=None,
                       amplitude=None,
                       undersampling=None,
                       increment=None,
                       duration=None,
                       comment=None):
    '''
    do multiple IV measurements at different temperatures for the NEP analysis
    '''
    
    #####################################
    # defaults
    if asicNum is None: asicNum = default_setting['asicNum']
    if Voffset is None: Voffset = default_setting['Voffset']
    if amplitude is None: amplitude = default_setting['amplitude']
    if undersampling is None: undersampling = default_setting['undersampling']
    if increment is None: increment = default_setting['increment']
    if duration is None: duration = default_setting['duration']
    if comment is None: comment = 'NEP sequence sent by pystudio'

    Tbath_list = [0.420,0.380,0.360,0.340,0.330,0.320,0.310]
    for Tbath in Tbath_list:
        self.do_IV_measurement(asicNum,Voffset,amplitude,undersampling,increment,Tbath,duration,comment)

    print('%s - NEP measurement completed' % utcnow().strftime('%Y-%m-%d %H:%M:%S'))
    return

def do_skydip(self,Voffset=None,azstep=None,azmin=None,azmax=None,elmin=None,elmax=None,comment=None):
    '''
    do the skydip sequence
    '''
    mount = obsmount()
    
    #####################################
    # defaults    
    if comment is None: comment = 'Sky Dip sequence sent by pystudio'
    if Voffset is None: Voffset = default_setting['Voffset']
    asicNum = default_setting['asicNum']
    
    if azstep is None: azstep = mount.azstep
    if azmin is None:
        azmin = mount.azmin
    else:
        mount.azmin = azmin
        
    if azmax is None:
        azmax = mount.azmax
    else:
        mount.azmax = azmax
        
    if elmin is None:
        elmin = mount.elmin
    else:
        mount.elmin = elmin
        
    if elmax is None:
        elmax = mount.elmax
    else:
        mount.elmax = elmax

    #####################################
    # configure the bolometers

    # stop all regulations
    ack = self.send_stopFLL(asicNum)

    # configure continuous bias
    ack = self.send_TESDAC_CONTINUOUS(asicNum,Voffset)

    # start all regulations
    ack = self.send_startFLL(asicNum)

    # start recording data
    dataset_name = 'SkyDip'
    ack = self.send_startAcquisition(dataset_name,comment)

    # run the Sky Dip sequency from obsmount
    mount.do_skydip_sequence(azstep)

    # stop the acquisition
    ack = self.send_stopAcquisition()

    print('%s - Sky Dip completed' % utcnow().strftime('%Y-%m-%d %H:%M:%S'))
    return

def do_scan(self):
    '''
    do a scan
    '''
    return


    
            
              
        
