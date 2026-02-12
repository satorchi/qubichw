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
import os,time
import numpy as np
from satorchipy.datefunctions import utcnow
from qubichk.imacrt import iMACRT
from qubichk.obsmount import obsmount
from qubichk.utilities import read_DACoffsetTables, shellcommand, verify_directory
from qubicpack.utilities import interpret_rawmask

#####################################
# defaults
default_setting = {}
default_setting['asicNum'] = [1,2] # both ASICs
default_setting['AcqMode'] = 0
default_setting['undersampling'] = 1000
default_setting['increment'] = 1
default_setting['Apol'] = 7
default_setting['RawMask'] = np.zeros(125,dtype=int)
default_setting['RawMask'][0] = 0xFF # 1-8
default_setting['RawMask'][6] = 0x3F # 51-56
default_setting['RawMask'][7] = 0xC0 # 57-58
default_setting['nsamples'] = 100
# default_setting['CycleRawMode'] = 0xFFFF
# default_setting['CycleRawMode'] = 0xFF * np.ones(16,dtype=int)
default_setting['CycleRawMode'] = 0 # reverse engineering: 2025-08-20 14:49:59
default_setting['Vicm'] = 3
default_setting['Vocm'] = 3
default_setting['startRow'] = 0
default_setting['lastRow'] = 31
default_setting['column'] = 3
default_setting['feedbackTable'] = np.zeros(128,dtype=float)
default_setting['PID'] = (0,40,0)
    
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

default_setting['ASIC 1']['offsetTable'] = np.zeros(128,dtype=float)
default_setting['ASIC 2']['offsetTable'] = np.zeros(128,dtype=float)
squid_group1 = [1.29,0.75,0.8,-0.2]
squid_group2 = [0.45,0.8,-0.2,-0.2]
for group_idx in range(4):
    start_idx = group_idx*32
    end_idx = start_idx + 32
    default_setting['ASIC 1']['offsetTable'][start_idx:end_idx] = squid_group1[group_idx]
    default_setting['ASIC 2']['offsetTable'][start_idx:end_idx] = squid_group2[group_idx]


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


def init_frontend(self,
                  asicNum=None,
                  nsamples=None,
                  AcqMode=None,
                  Apol=None,
                  Spol=None,
                  Vicm=None,
                  Vocm=None,
                  startRow=None,
                  lastRow=None,
                  column=None,
                  CycleRawMode=None,
                  RawMask=None,
                  FeedbackRelay=None,
                  Aplitude=None,
                  offsetTable=None,
                  feedbackTable=None,
                  PID=None
                  ):
    '''
    initialize the readout ASICs.
    This is done immediately after power up and flashing the fpga
    see:  https://qubic.in2p3.fr/wiki/TD/Starting#toc-4

    translated from Michel's javascript:  Asics_init.dscript
    '''

    # set the defaults if not given explicitly
    if asicNum is None: asicNum = self.get_default_setting('asicNum')
    if nsamples is None: nsamples = self.get_default_setting('nsamples')
    if AcqMode is None: AcqMode = self.get_default_setting('AcqMode')
    if Apol is None: Apol = self.get_default_setting('Apol')
    if Vicm is None: Vicm = self.get_default_setting('Vicm')
    if Vocm is None: Vocm = self.get_default_setting('Vocm')
    if startRow is None: startRow = self.get_default_setting('startRow')
    if lastRow is None: lastRow = self.get_default_setting('lastRow')
    if column is None: column = self.get_default_setting('column')
    if CycleRawMode is None: CycleRawMode = self.get_default_setting('CycleRawMode')
    if RawMask is None: RawMask = self.get_default_setting('RawMask')
    if FeedbackRelay is None: FeedbackRelay = self.get_default_setting('FeedbackRelay',measurement='observation')
    if Aplitude is None: Aplitude = self.get_default_setting('Aplitude',measurement='observation')
    if feedbackTable is None: feedbackTable = self.get_default_setting('feedbackTable')
    if PID is None: PID = self.get_default_setting('PID')

    # configure the frontend
    ack = self.send_NSample(asicNum,nsamples)
    time.sleep(1.0)
    ack = self.send_AcqMode(asicNum,0)
    time.sleep(1.0)
    ack = self.send_Apol(asicNum, Apol)

    # special case for Spol and DAC offsets which are different for each ASIC
    if isinstance(asicNum,list):
        for asic in asicNum:
            if Spol is None:
                ack = self.send_Spol(asic,self.get_default_setting('Spol',asic=asic))
            else:
                ack =self.send_Spol(asic,Spol)
                
            if offsetTable is None:
                ack = self.send_offsetTable(asic,self.get_default_setting('offsetTable',asic=asic))
            else:
                ack = self.send_offsetTable(asic,offsetTable)
    else:
        if Spol is None: 
            ack = self.send_Spol(asicNum,self.get_default_setting('Spol',asic=asicNum))
        else:
            ack = self.send_Spol(asicNum,Spol)
            
        if offsetTable is None:
            ack = self.send_offsetTable(asicNum,self.get_default_setting('offsetTable',asic=asicNum))
        else:
            ack = self.send_offsetTable(asicNum,offsetTable)
    
    ack = self.send_Vicm(asicNum, Vicm)
    ack = self.send_Vocm(asicNum, Vocm)
    ack = self.send_lastRow(asicNum,lastRow)
    ack = self.send_startRow(asicNum,startRow)
    ack = self.send_setColumn(asicNum,column)
    ack = self.send_CycleRawMode(asicNum, CycleRawMode)
    time.sleep(1.0)
    ack = self.send_RawMask(asicNum,RawMask)
    ack = self.send_AsicInit(asicNum)
    time.sleep(1.0)
    ack = self.send_AsicConf(asicNum,2,3)
    time.sleep(1.0)
    ack = self.send_AsicConf(asicNum,2,0)
    time.sleep(1.0)
    ack = self.send_AsicInit(asicNum)
    time.sleep(1.0)
    ack = self.send_FeedbackRelay(asicNum,FeedbackRelay)
    time.sleep(1.0)
    ack = self.send_Aplitude(asicNum,Aplitude)

    ack = self.send_configurePID(asicNum,PID[0],PID[1],PID[2])
    ack = self.send_AsicInit(asicNum)    

    ack = self.park_frontend()
    return
                  

def set_bath_temperature(self,Tbath,timeout=120,precision=0.003):
    '''
    set the iMACRT PID for the desired temperature and wait until it reaches the temperature
    '''
    # get current temperature
    mgc = iMACRT(device='mgc')
    Tmeas = mgc.get_mgc_measurement()
    if Tmeas is None or Tmeas=='':
        print('Could not get temperature from MGC3.')
        return None
    else:
        print('Tbath is currently: %.3f mK' % (Tmeas*1000))

    
    ans = mgc.set_mgc_setpoint(Tbath)
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


def do_DACoffset_measurement(self,duration=None,Tbath=None,Voffset=None,comment=None):
    '''
    run a short acquisition with DAC offsets set to zero
    afterwards, this dataset is used to calculate the DACoffsetTable

    we don't change the current settings except to put zeros in the DACoffsetTable
    '''
    if duration is None: duration = 30
    
    dataset_name = 'DACoffsetMeasurement'
    comment = 'sent by pystudio'
    asicNum = [1,2]

    # make sure FLL is stopped
    
    
    # set the offset table to zero
    offset_table = np.zeros(128,dtype=float)
    ack = self.send_offsetTable(asicNum,offset_table)

    # start an acquisition, but with no FLL regulations
    ack = self.start_observation(Tbath=Tbath,Voffset=Voffset,FLL=False,comment=comment,title='DAC_offset_measurement')

    time.sleep(duration)
    ack = self.end_observation()
    return

def assign_saved_DACoffsetTables(self):
    '''
    assign the DAC offset table for each ASIC reading the table from file
    the files are found by default in $HOME/.local/share/qubic
    '''
    offsetTables = read_DACoffsetTables()
    for asic_num in offsetTables.keys():
        ack = self.send_offsetTable(asic_num,offsetTables[asic_num])
        
    return ack

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
    if Tmeas is None or Tmeas=='':
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
    if asicNum is None: asicNum = self.get_default_setting('asicNum',measurement='I-V')
    if Voffset is None: Voffset = self.get_default_setting('Voffset',measurement='I-V')
    if amplitude is None: amplitude = self.get_default_setting('amplitude',measurement='I-V')
    if undersampling is None: undersampling = self.get_default_setting('undersampling',measurement='I-V')
    if increment is None: increment = self.get_default_setting('increment',measurement='I-V')
    if duration is None: duration = self.get_default_setting('duration',measurement='I-V')
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


def set_observation_mode(self,Voffset=None,Tbath=None,FLL=True):
    '''
    setup the frontend for observing but do not start the acquisition
    '''
    #####################################
    # defaults
    if Voffset is None: Voffset = 3.0
    asicNum = default_setting['asicNum']

    #####################################
    # check for desired bath temperature
    #  maybe this is too much error checking, and too easily aborted

    # get current temperature
    mgc = iMACRT(device='mgc')
    Tmeas = mgc.get_mgc_measurement()
    if Tmeas is None or Tmeas=='':
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

    # start all regulations.  Optionally, do not start regulations
    if FLL: ack = self.send_startFLL(asicNum)

    return

def start_acquisition(self,title=None,comment=None):
    '''
    start the data acquisition
    '''
    #####################################
    # defaults
    if title is None: title = 'observation'
    if comment is None: comment = 'observation sent by pystudio'
    
    # start recording data
    acq_start = utcnow()
    ack = self.send_startAcquisition(title,comment)

    # get the assigned dataset name
    parm_name = 'DISP_BackupSessionName_ID'
    vals = self.send_request(parameterList=[parm_name])
    if parm_name not in vals.keys():
        dataset_name = '%s__%s' % (acq_start.strftime('%Y-%m-%d_%H.%M.%S'),title)
        print('WARNING! could not get assigned dataset name.  Using: %s' % dataset_name)
    else:
        dataset_name = vals[parm_name]['value']

    # start dumping the azel data
    day_str = acq_start.strftime('%Y-%m-%d')
    dump_dir = os.sep.join([os.environ['HOME'],day_str,dataset_name,'Hks'])
    dump_dir = verify_directory(dump_dir)
    if dump_dir is None:
        dump_dir = os.sep.join([os.environ['HOME'],'data'])
        dump_dir = verify_directory(dump_dir)
        
    if dump_dir is None:
        dump_dir = '/tmp'

    if self.verbosity>2:        
        print('Dumping in directory: %s' % dump_dir)
        
    cmd = 'start_mountplc_acquisition.sh %s' % dump_dir
    out,err = shellcommand(cmd)
   
    print('%s - %s started' % (utcnow().strftime('%Y-%m-%d %H:%M:%S'),title))
    return

def start_observation(self,Voffset=None,Tbath=None,title=None,comment=None,FLL=True):
    '''
    setup the frontend for observing and start the acquisition
    '''
    #####################################
    # defaults
    if title is None: title = 'observation'
    if comment is None: comment = 'observation sent by pystudio'
    if Voffset is None: Voffset = 3.0

    ack = self.set_observation_mode(Voffset=Voffset,Tbath=Tbath,FLL=FLL)
    ack = self.start_acquisition(title=title,comment=comment)
    
    return

def end_observation(self):
    '''
    stop acquisition and stop regulations
    '''
    ack = self.send_stopAcquisition()
    ack = self.send_stopFLL()
    # stop Az/El acquisition
    cmd = 'screen -X -S mountPLC quit'
    out,err = shellcommand(cmd)
    if len(err)>0:
        print('%s - error ending Az/El acquisition: %s' % (utcnow().strftime('%Y-%m-%d %H:%M:%S'),err))
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
    ack = self.end_observation()
    
    print('%s - Sky Dip completed' % utcnow().strftime('%Y-%m-%d %H:%M:%S'))
    return


def get_frontend_settings(self,parameterList=None):
    '''
    build a nice text message containing the current frontend settings
    '''

    if parameterList is None:
        parameterList = self.default_parameterList

    txt = {}
    txt['common'] = []
    for idx in range(16):
        key = 'ASIC %2i' % (idx+1)
        txt[key] = []

    txt['ERROR'] = []

    # it seems the request only works for one parameter at a time,
    # even though it seems to be built to return multiple parameters
    for parm_name in parameterList:
        vals = self.send_request(parameterList=[parm_name])
        if 'bytes' not in vals.keys():
            txt['ERROR'].append(parm_name+'\n   ')
            txt['ERROR'].append('\n   '.join(vals['ERROR']))
            continue

        if self.verbosity>2:
            # save response for debugging
            fname = '%s_request.dat' % parm_name
            h = open(fname,'wb')
            h.write(vals['bytes'])
            h.close()

        if parm_name not in vals.keys(): continue

        parm_vals = vals[parm_name]['value']

        if isinstance(parm_vals,str):
            line = '%s = %s' % (parm_name,parm_vals)
            txt['common'].append(line)
            continue

        if isinstance(parm_vals,np.ndarray):
            if len(parm_vals)>16:
                line = '%s = %s' % (parm_name,parm_vals)
                txt['common'].append(line)
                continue
            
            if parm_vals.dtype=='float':
                for idx,val in enumerate(parm_vals):
                    key = 'ASIC %2i' % (idx+1)
                    line = '%s = %.2f' % (parm_name,val)
                    txt[key].append(line)
                continue

            if parm_vals.dtype=='int':
                for idx,val in enumerate(parm_vals):
                    key = 'ASIC %2i' % (idx+1)
                    line = '%s = %i' % (parm_name,val)
                    txt[key].append(line)
                continue

        if isinstance(parm_vals,list):
            if len(parm_vals)>16:
                line = '%s = %s' % (parm_name,parm_vals)
                txt['common'].append(line)
                continue
        
            for idx,val in enumerate(parm_vals):
                key = 'ASIC %2i' % (idx+1)
                line = '%s = %s' % (parm_name,val)
                txt[key].append(line)
            continue

        if parm_vals is None:
            line = '%s = %s' % (parm_name,vals[parm_name]['text'])
            txt['common'].append(line)
            continue

        line = '%s = %s' % (parm_name,parm_vals)
        txt['common'].append(line)

    line = ' QUBIC FRONTEND STATUS '.center(80,'*')
    lines = [line]
    lines += txt['common']

    # we only print for 2 ASICs even though there is default data for 16 ASICs
    # change this when we have the full instrument
    for idx in range(self.NASIC):
        key = 'ASIC %2i' % (idx+1)
        if key not in txt.keys(): continue
        if len(txt[key])==0: continue
        
        ttl = ' %s ' % key
        line = '\n'+ttl.center(80,'*')
        lines.append(line)
        lines += txt[key]

    if len(txt['ERROR'])>0:
        lines.append('\n'+' ERROR! '.center(80,'*'))
        lines += txt['ERROR']
    msg = '\n'.join(lines)
    return msg

def do_scan(self):
    '''
    do a scan
    '''
    return


    
            
              
        
