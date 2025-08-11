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
default_setting['undersampling'] = 1000
default_setting['increment'] = 1
default_setting['Apol'] = 7

default_setting['elmin'] = 50 # minimum permitted elevation
default_setting['elmax'] = 70 # maximum permitted elevation
default_setting['azmin'] = 61  # minimum permitted azimuth
default_setting['azmax'] = 115 # maximum permitted azimuth (changed to 25 on 2025-06-06 15:51:25 UT)
default_setting['azstep'] = 5 # default step size for azimuth movement for skydips

default_setting['I-V'] = {}
default_setting['I-V']['Voffset'] = 5.5
default_setting['I-V']['amplitude'] = 7.0
default_setting['I-V']['duration'] = 120
default_setting['I-V']['Aplitude'] = 180
default_setting['I-V']['FeedbackRelay'] = 10

default_setting['SQUID'] = {}
default_setting['SQUID']['Voffset'] = 8
default_setting['SQUID']['amplitude'] = 1
default_setting['SQUID']['duration'] = 2
default_setting['SQUID']['Aplitude'] = 1800

default_setting['observation'] = {}
default_setting['observation']['Voffset'] = 3.0
default_setting['observation']['Aplitude'] = 1800
default_setting['observation']['FeedbackRelay'] = 100

default_setting['ASIC 1'] = {}
default_setting['ASIC 2'] = {}

default_setting['ASIC 1']['Spol'] = 10
default_setting['ASIC 2']['Spol'] = 12

def get_default_setting(self,parm=None,asic=None,measurement=None):
    '''
    get the default value, for a particular ASIC is requested
    '''

    if parm in default_setting.keys():
        return default_setting[parm]

    if asic is None and measurement is None:
        return None

    if asic is not None:
        asicKey = 'ASIC %i' % asic
        
    if measurement in default_setting.keys():
        if asic is not None and asicKey in default_setting[measurement].keys():
            if parm in default_setting[measurement][asicKey].keys():
                return default_setting[measurement][asicKey][parm]
        if parm in default_setting[measurement].keys():
            return default_setting[measurement][parm]
            
    if asic is None:
        return None
            
    if asicKey not in default_setting.keys():
        return None

    if parm not in default_setting[asicKey].keys():
        return None

    return default_setting[asicKey][parm]
        

def set_bath_temperature(self,Tbath,timeout=120,precision=0.003):
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
    if asicNum is None: asicNum = self.get_default_setting('asicNum')
    if Voffset is None: Voffset = self.get_default_setting('Voffset',measurement='I-V')
    if amplitude is None: amplitude = self.get_default_setting('amplitude',measurement='I-V')
    if undersampling is None: undersampling = self.get_default_setting('undersampling',measurement='I-V')
    if increment is None: increment = self.get_default_setting('increment',measurement='I-V')
    if duration is None: duration = self.get_default_setting('duration',measurement='I-V')
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

    # set feedback relay for I-V measurement
    ack = self.send_FeedbackRelay(asicNum,10)

    # set Aplitude corresponding to 10kOhm feedback relay
    ack = self.send_Aplitude(asicNum,180)

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
        dataset_name = 'IV_%.0fmK' % (1000*Tmeas)
    ack = self.send_startAcquisition(dataset_name,comment)

    # wait for measurement
    time.sleep(duration)

    # stop the acquisition
    ack = self.send_stopAcquisition()

    # stop the FLL
    ack = self.send_stopFLL(asicNum)

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


def do_SQUID_optimization(self,
                          asicNum=None,
                          Voffset=None,
                          amplitude=None,
                          undersampling=None,
                          increment=None,
                          Tbath=None,
                          duration=None,
                          aplitude=None,
                          Apol=None,
                          comment=None):
    '''
    run the sequence to measure the SQUID optimum bias
    '''

    #####################################
    # defaults
    if asicNum is None: asicNum = self.get_default_setting('asicNum')
    if Voffset is None: Voffset = self.get_default_setting('Voffset',measurement='SQUID')
    if amplitude is None: amplitude = self.get_default_setting('amplitude',measurement='SQUID')
    if undersampling is None: undersampling = self.get_default_setting('undersampling',measurement='SQUID')
    if increment is None: increment = self.get_default_setting('increment',measurement='SQUID')
    if duration is None: duration = self.get_default_setting('duration',measurement='SQUID')
    if aplitude is None: aplitude = self.get_default_setting('Aplitude',measurement='SQUID')
    if Apol is None: Apol = self.get_default_setting('Apol',measurement='SQUID')
    if comment is None: comment = 'SQUID optimization measurement sent by pystudio'
    if Tbath is None: Tbath = 0.420

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
    Tbath_ok = self.set_bath_temperature(Tbath)

    if not Tbath_ok:
        print("Tbath temperature not reached.  I'm not continuing with the SQUID optimization measurement.")
        return None


    #####################################
    # configure the bolometers

    # stop all regulations
    ack = self.send_stopFLL(asicNum)

    # set the Aplitude (Amplitude Modulation)
    ack = self.send_Aplitude(asicNum,aplitude)

    # set the SQUID amplitude (Apol)
    ack = self.send_Apol(asicNum,Apol)

    # configure sine curve bias
    ack = self.send_TESDAC_SINUS(asicNum,amplitude,Voffset,undersampling,increment)

    # get current temperature
    mgc = iMACRT(device='mgc')
    Tmeas = mgc.get_mgc_measurement()
    if Tmeas=='':
        T_str = ''
    else:
        T_str = '%.0fmK' % (1000*Tmeas)

    
    # loop through the Spol values
    for bias_index in range(16):
        # set the Spol value
        ack = self.send_Spol(asicNum,bias_index)
        time.sleep(0.1)
        
        dataset_name = 'SQUIDs_opt_bias_aplitude_%i_%i' % (aplitude,bias_index)
        ack = self.send_startAcquisition(dataset_name,comment)

        # wait for measurement
        time.sleep(duration)

        # stop the acquisition
        ack = self.send_stopAcquisition()


    # switch off the temperature feedback
    mgc.set_mgc_pid(0)
    mgc.disconnect()
    
    print('%s - SQUID optimization measurement completed' % utcnow().strftime('%Y-%m-%d %H:%M:%S'))
    return


def start_observation(self,Voffset=None,Tbath=None,title=None,comment=None):
    '''
    setup the frontend for observing and start the acquisition
    '''
    #####################################
    # defaults
    if title is None: title = 'observation'
    if comment is None: comment = 'observation sent by pystudio'
    if Voffset is None: Voffset = 3.0
    asicNum = default_setting['asicNum']

    #####################################
    # check for desired bath temperature
    #  maybe this is too much error checking, and too easily aborted

    # get current temperature
    mgc = iMACRT(device='mgc')
    Tmeas = mgc.get_mgc_measurement()
    if Tmeas=='':
        print('ERROR! Could not get temperature from MGC3.  aborting')
        return None
    
    print('Tbath is currently: %.3f mK' % (Tmeas*1000))
    
    if Tbath is None:
        print('WARNING!  TES bath temperature not specified. Using current temperature')
        Tbath = Tmeas
    Tbath_ok = self.set_bath_temperature(Tbath)

    if not Tbath_ok:
        print("Tbath temperature not reached.  aborting.")
        return None
    
    #####################################
    # configure the bolometers

    # stop all regulations
    ack = self.send_stopFLL(asicNum)

    # set feedback relay for normal measurement
    ack = self.send_FeedbackRelay(asicNum,100)

    # set Aplitude corresponding to 100kOhm feedback relay
    ack = self.send_Aplitude(asicNum,1800)

    # configure continuous bias
    ack = self.send_TESDAC_CONTINUOUS(asicNum,Voffset)

    # start all regulations
    ack = self.send_startFLL(asicNum)

    # start recording data
    ack = self.send_startAcquisition(title,comment)
   
    print('%s - %s started' % (utcnow().strftime('%Y-%m-%d %H:%M:%S'),title))
    return

def end_observation(self):
    '''
    stop acquisition and stop regulations
    '''
    ack = self.send_stopAcquisition()
    ack = self.send_stopFLL()
    print('%s - observation ended' % (utcnow().strftime('%Y-%m-%d %H:%M:%S')))
    return

def park_frontend(self):
    '''
    set the frontend into "parking" mode
    '''
    asicNum = default_setting['asicNum']
    # stop all regulations
    ack = self.send_stopFLL(asicNum)

    # set feedback relay for normal observation measurement
    ack = self.send_FeedbackRelay(asicNum,100)

    # set Aplitude corresponding to 100kOhm feedback relay
    ack = self.send_Aplitude(asicNum,1800)

    # configure sine curve bias
    amplitude = 1
    Voffset = 8
    undersampling = 1000
    increment = 1
    ack = self.send_TESDAC_SINUS(asicNum,amplitude,Voffset,undersampling,increment)

    # switch off the temperature feedback loop
    mgc = iMACRT(device='mgc')
    ans = mgc.set_mgc_pid(0)
    mgc.disconnect()
    
    print('%s - frontend parked' % (utcnow().strftime('%Y-%m-%d %H:%M:%S')))
    return

def do_skydip(self,Voffset=None,Tbath=None,azstep=None,azmin=None,azmax=None,elmin=None,elmax=None,comment=None):
    '''
    do the skydip sequence
    '''
    mount = obsmount()
    
    #####################################
    # defaults    
    if comment is None: comment = 'Sky Dip sequence sent by pystudio'
    dataset_name = 'SkyDip'

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
    # setup and start the acquisition
    self.start_observation(Voffset,Tbath,dataset_name,comment)

    # run the Sky Dip sequency from obsmount
    mount.do_skydip_sequence(azstep)
    mount.disconnect()

    # stop the acquisition
    ack = self.send_stopAcquisition()

    # stop the FLL
    ack = self.send_stopFLL(asicNum)
    
    print('%s - Sky Dip completed' % utcnow().strftime('%Y-%m-%d %H:%M:%S'))
    return


def do_scan(self):
    '''
    do a scan
    '''
    return


    
            
              
        
