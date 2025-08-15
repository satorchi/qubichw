'''
$Id: frontend.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 23 Jul 2025 18:06:25 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

setup commands to the dispatcher related to setting up the bolometers
'''
import numpy as np

def asic_qsnumber(self,asicNum):
    '''
    ASIC bit number

    note: 2025-07-28 10:38:27

    AsicNum in QubicStudio is not the same as what is used in the user interface
    there is bitmasking possible so that the command can be sent to multiple ASICs
    for example give asicNum = '1' | '2' and it will send to both 1 and 2.
    that means that the asicNum is actually a bit place in a 24 bit word
    asic 1 is bit 8
    asic 2 is bit 9
    I'm not sure why it's not bit 0 and bit 1, but there you go
    presumeably, when we have the full instrument, the 16 ASICs will go from bit-8 to bit-23 inclusive
    '''
    bitplace = asicNum + 7
    qsAsicNum = 2**bitplace
    return qsAsicNum

def Voffset2ADU(self,Voffset):
    '''
    convert the bias offset in Volts to ADU
    transfer function taken from the Transfer Function Editor on QubicStudio
    file: parametersTF.dispatcher
    function=288.58e-6x + 0.0
    '''

    ADUfloat = np.abs(Voffset)/288.58e-6
    ADU = round(ADUfloat)
    if Voffset<0:
        return (ADU | 2**15)
    return ADU

def ADU2Voffset(self,ADU):
    '''
    convert the bias offset ADU returned by dispatcher to Volts
    '''
    Voffset = 288.58e-6*ADU
    return Voffset

def amplitude2ADU(self,amplitude):
    '''
    convert the TES bias sine amplitude to ADU

    transfer function taken from the Transfer Function Editor on QubicStudio
    file: parametersTF.dispatcher
    function=1.15432e-3x + 0.0
    '''

    ADUfloat = amplitude/1.15432e-3
    ADU = round(ADUfloat)
    return ADU

def ADU2amplitude(self,ADU):
    '''
    convert the TES bias sine amplitude from ADU to Volts
    '''
    amplitude = ADU*1.15432e-3
    return amplitude

def offsetDACvalue2ADU(self,offsetDACvalue):
    '''
    convert the TES offset DAC value to ADU
    see parameterTF.dispatcher
    '''
    ADUfloat = np.abs(offsetDACvalue)/1.4215e-4
    ADU = round(ADUfloat)
    if offsetDACvalue<0:
        return (ADU | 2**15)
    return ADU

def ADU2offsetDACvalue(self,ADU):
    '''
    convert an ADU value to the offsetDACvalue
    '''
    offsetDACvalue = ADU*1.4215e-4
    return offsetDACvalue

def feedbackDACvalue2ADU(self,feedbackDACvalue):
    '''
    convert the TES offset DAC value to ADU
    see parameterTF.dispatcher
    '''
    ADUfloat = feedbackDACvalue/284.3e-6
    ADU = round(ADUfloat)
    return ADU

def ADU2feedbackDACvalue(self,ADU):
    '''
    convert an ADU value to the feedbackDACvalue
    '''
    feedbackDACvalue = ADU*284.3e-6
    return feedbackDACvalue

def make_frontend_preamble(self,asicNum_list,subsysID1,subsysID2):
    '''
    make the first bytes of a frontend command

    we can configure any number of ASICs the same way.  
    If the asicNum argument is a list, then make a bitmask for all the requested ASICs
    '''
    if asicNum_list is None:
        asicNum_list = self.get_default_setting('asicNum')
        
    if isinstance(asicNum_list,list):
        qsAsicNum = 0
        for asicNum in asicNum_list:
            qsAsicNum = (qsAsicNum | self.asic_qsnumber(asicNum))
    else:
        asicNum = asicNum_list
        qsAsicNum = self.asic_qsnumber(asicNum)
    
    cmd_bytes_list = [self.SEND_TC_TO_SUBSYS_ID,
                      self.MULTINETQUICMANAGER_ID,
                      (subsysID1 & 0xFF00) >> 8,
                      (subsysID1 & 0x00FF)]
    cmd_bytes_list.append( (qsAsicNum & 0xFF0000) >> 16 )
    cmd_bytes_list.append( (qsAsicNum & 0x00FF00) >> 8 ) 
    cmd_bytes_list.append( (qsAsicNum & 0x0000FF) )
    cmd_bytes_list.append(0xaa)
    cmd_bytes_list.append(0x55)
    cmd_bytes_list.append(subsysID2)
    cmd_bytes_list.append(0x00)
    return cmd_bytes_list

def make_frontend_suffix(self,cmd_bytes_list):
    '''
    add the final bytes to the frontend command
    '''
    cmd_bytes_list.append(0xfa)
    cmd_bytes_list.append(0xda)
    return cmd_bytes_list

def make_command_startstopFLL(self,asicNum,onOff):
    '''
    make the command to start or stop the FLL
    '''
    if asicNum is None:
        asicNum = self.get_default_setting('asicNum')
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_ACTIVATEPID_ID,0x14)
    cmd_bytes_list.append( (onOff & 0xFF00) >> 8 ) 
    cmd_bytes_list.append( (onOff & 0x00FF) )
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)

    return self.make_communication_packet(cmd_bytes_list)
    
def send_startFLL(self,asicNum=None):
    '''
    start the bolometer feedback regulations
    '''
    cmd_bytes = self.make_command_startstopFLL(asicNum,1)
    ack = self.send_command(cmd_bytes)
    
    return ack

def send_stopFLL(self,asicNum=None):
    '''
    stop the bolometer feedback regulations
    '''
    cmd_bytes = self.make_command_startstopFLL(asicNum,0)
    ack = self.send_command(cmd_bytes)
    
    return ack

def make_command_TESDAC_SINUS(self,asicNum,amplitude,Voffset,undersampling,increment):
    '''
    make the command to configure sine modulation on the TES bias
    '''
    amplitudeADU = self.amplitude2ADU(amplitude)
    VoffsetADU = self.Voffset2ADU(Voffset)
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETTESDAC_SINUS_ID,0x42)
    cmd_bytes_list.append( ((VoffsetADU & 0xFF00) >> 8)) 
    cmd_bytes_list.append( ((VoffsetADU & 0x00FF)))
    cmd_bytes_list.append( ((amplitudeADU & 0xFF00) >> 8)) 
    cmd_bytes_list.append( ((amplitudeADU & 0x00FF)))
    cmd_bytes_list.append( ((undersampling & 0xFF00) >> 8)) 
    cmd_bytes_list.append( ((undersampling & 0x00FF)))
    cmd_bytes_list.append( ((increment & 0xFF)))
    cmd_bytes_list.append(0x00)
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)

    return self.make_communication_packet(cmd_bytes_list)

def send_TESDAC_SINUS(self,asicNum,amplitude,Voffset,undersampling,increment):
    '''
    send the command to configure sine modulation on the TES bias
    '''
    cmd_bytes = self.make_command_TESDAC_SINUS(asicNum,amplitude,Voffset,undersampling,increment)
    ack = self.send_command(cmd_bytes)
    return ack
    
def make_command_TESDAC_CONTINUOUS(self,asicNum,Voffset):
    '''
    make the command to configure constant TES bias voltage
    '''
    VoffsetADU = self.Voffset2ADU(Voffset)
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETTESDAC_CONTINUE_ID,0x40)
    cmd_bytes_list.append( ((VoffsetADU & 0xFF00) >> 8)) 
    cmd_bytes_list.append( ((VoffsetADU & 0x00FF)))
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)

    return self.make_communication_packet(cmd_bytes_list)
    
def send_TESDAC_CONTINUOUS(self,asicNum,Voffset):
    '''
    send the command to configure constant TES bias voltage
    '''
    cmd_bytes = self.make_command_TESDAC_CONTINUOUS(asicNum,Voffset)
    ack = self.send_command(cmd_bytes)
    return ack

def make_command_get_frontend_status(self,asicNum):
    '''
    make the command to query the dispatcher for the status (this is not the details of all the parameters)
    '''
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_GETSTATUS_ID,0x0E)
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)
    return self.make_communication_packet(cmd_bytes_list)

def get_frontend_status(self,asicNum):
    '''
    query the dispatcher for the current settings
    '''
    cmd_bytes = self.make_command_get_frontend_status(asicNum)
    ack = self.send_command(cmd_bytes)
    return ack

def make_command_FeedbackRelay(self,asicNum,FLLrelay):
    '''
    make the command to set the FLL relay resistance

    There are only two possibilities for the FLL relay:  10kOhm or 100kOhm
    '''

    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETFEEDBACKRELAY_ID,0x30)
    cmd_bytes_list.append(0x00)
    if FLLrelay<100:
        cmd_bytes_list.append(0x00)
    else:
        cmd_bytes_list.append(0x01)
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)
    return self.make_communication_packet(cmd_bytes_list)

def send_FeedbackRelay(self,asicNum,FLLrelay):
    '''
    send the command to set the FLL relay resistance
    '''
    cmd_bytes = self.make_command_FeedbackRelay(asicNum,FLLrelay)
    ack = self.send_command(cmd_bytes)
    return ack

def make_command_Aplitude(self,asicNum,aplitude):
    '''
    set the so-called "Aplitude"
    It's a mulitplier for the TOD
    It should be 180 when the Feedback Relay is 10kOhm
            and 1800 when the Feedback Relay is 100kOhm

    QubicStudio does not mask the ASIC number in the usual way for this (see above method asic_qsnumber)
    Instead, there is only "Send to all" possible, and the ASIC is set to 0x0000FF (I would have guessed it should be 0xFFFF00)
    In fact, the usual ASIC masking works as above.  (tested 2025-07-30 15:28:01)

    the Aplitude is set directly from the input integer.  There is no transfer function. (see file parametersTF.dispatcher)
    
    example output from the dispatcher logbook:

    sets Aplitude to 180:
     SetModulationAmplitude (size=11):00 00 FF AA 55 32 00 00 B4 FA DA

    sets Aplitude to 1800
     SetModulationAmplitude (size=11):00 00 FF AA 55 32 00 07 08 FA DA
    '''
    aplitudeADU = round(aplitude)

    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETAPLITUDE_ID,0x32)
    cmd_bytes_list.append( ((aplitudeADU & 0xFF00) >> 8)) 
    cmd_bytes_list.append( ((aplitudeADU & 0x00FF)))
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)

    return self.make_communication_packet(cmd_bytes_list)    

def send_Aplitude(self,asicNum,aplitude):
    '''
    send the command to set the Aplitude
    '''
    cmd_bytes = self.make_command_Aplitude(asicNum,aplitude)
    ack = self.send_command(cmd_bytes)
    return ack

    
def make_command_Spol(self,asicNum,Spol):
    '''
    make the command to set the SQUID bias
    '''
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETASICSPOL_ID,0x00)
    cmd_bytes_list.append( ((Spol & 0xF0) >> 4))
    cmd_bytes_list.append( ((Spol & 0x0F) << 4) |  0x04)
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)
    return self.make_communication_packet(cmd_bytes_list)

def send_Spol(self,asicNum,Spol):
    '''
    send the command to set SQUID bias
    '''
    cmd_bytes = self.make_command_Spol(asicNum,Spol)
    ack = self.send_command(cmd_bytes)
    return ack

def make_command_Apol(self,asicNum,Apol):
    '''
    make the command to set the SQUID amplitude
    '''
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETASICAPOL_ID,0x00)
    cmd_bytes_list.append( ((Apol & 0xF0) >> 4))
    cmd_bytes_list.append( ((Apol & 0x0F) << 4) |  0x04)
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)
    return self.make_communication_packet(cmd_bytes_list)

def send_Apol(self,asicNum,Apol):
    '''
    send the command to set SQUID amplitude
    '''
    cmd_bytes = self.make_command_Spol(asicNum,Apol)
    ack = self.send_command(cmd_bytes)
    return ack

def make_command_RawMask(self,asicNum,rawmask):
    '''
    set the raw mask

    the raw mask is an array of size 125, each represents a byte
    when all the bytes are concatenated together we get a bitmask of 1000 bits
    samples are masked out for bits that are 1 (it's sort of an anti-mask)
    
    '''
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETMASK_ID,0x03)
    for bytemask in rawmask:
        cmd_bytes_list.append( (bytemask & 0xFF) )
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)    
    return self.make_communication_packet(cmd_bytes_list)

def send_RawMask(self,asicNum,rawmask):
    '''
    send the raw mask configuration
    '''
    cmd_bytes = self.make_command_RawMask(asicNum,rawmask)
    ack = self.send_command(cmd_bytes)
    return ack

def make_command_NSample(self,asicNum,nsamples):
    '''
    make the command to set the number of samples in the pre-integration
    raw samples are binned by this amount, slowing down the data rate
    usually, we choose nsamples=100
    '''
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETNSAMPLE_ID,0x05)
    cmd_bytes_list.append( (nsamples & 0xFF00) >> 8 )
    cmd_bytes_list.append( (nsamples & 0x00FF)      )
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)    
    return self.make_communication_packet(cmd_bytes_list)

def send_NSample(self,asicNum,nsamples):
    '''
    send the command to set the number of samples
    '''
    cmd_bytes = self.make_command_NSample(asicNum,nsamples)
    ack = self.send_command(cmd_bytes)
    return ack
    
def make_command_AsicInit(self,asicNum):
    '''
    make the command to send "ASIC Init"
    '''
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETASICINIB_ID,0x10)
    cmd_bytes_list.append(0x00)
    cmd_bytes_list.append(0x01)
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)    
    return self.make_communication_packet(cmd_bytes_list)

def send_AsicInit(self,asicNum):
    '''
    send the ASIC Init command
    '''
    cmd_bytes = self.make_command_AsicInit()
    ack = self.send_command(cmd_bytes)
    return ack
    
def make_command_Vicm(self,asicNum,Vicm):
    '''
    make the command to set the Vicm... I don't know what this is
    '''
    
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETASICVICM_ID,0x00)
    # the following looks very weird to me... ask Wilfried (see tvirtualcommandencode.cpp)
    cmd_bytes_list.append( (Vicm & 0xF0) >> 4 )
    cmd_bytes_list.append( ((Vicm & 0x0F) << 4) |  0x02 )
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)
    return self.make_communication_packet(cmd_bytes_list)

def send_Vicm(self,asicNum,Vicm):
    '''
    send the Vicm
    '''
    cmd_bytes = self.make_command_Vicm(asicNum,Vicm)
    ack = self.send_command(cmd_bytes)
    return ack

def make_command_Vocm(self,asicNum,Vocm):
    '''
    make the command to set the Vocm... I don't know what this is
    '''
    
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETASICVOCM_ID,0x00)
    # the following looks very weird to me... ask Wilfried (see tvirtualcommandencode.cpp)
    cmd_bytes_list.append( (Vocm & 0xF0) >> 4 )
    cmd_bytes_list.append( ((Vocm & 0x0F) << 4) |  0x03 )
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)
    return self.make_communication_packet(cmd_bytes_list)

def send_Vocm(self,asicNum,Vocm):
    '''
    send the Vocm
    '''
    cmd_bytes = self.make_command_Vocm(asicNum,Vocm)
    ack = self.send_command(cmd_bytes)
    return ack

def make_command_AcqMode(self,asicNum,mode):
    '''
    make the command to set the acquisition mode
    '''
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETACQMODE_ID,0x09)
    cmd_bytes_list.append( (mode & 0xFF00) >> 8)
    cmd_bytes_list.append( (mode & 0x00FF)     )
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)
    return self.make_communication_packet(cmd_bytes_list)

def send_AcqMode(self,asicNum,mode):
    '''
    send the Acquisition Mode
    '''
    cmd_bytes = self.make_command_AcqMode(asicNum,mode)
    ack = self.send_command(cmd_bytes)
    return ack

def make_command_startRow(self,asicNum,startrow):
    '''
    make the command to select the start row
    '''
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETASICSELSTARTROW_ID,0x00)
    cmd_bytes_list.append(  (startrow & 0xF0) >> 4           )
    cmd_bytes_list.append( ((startrow & 0x0F) << 4 ) |  0x06 )
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)
    return self.make_communication_packet(cmd_bytes_list)

def send_startRow(self,asicNum,startrow):
    '''
    send the select row command
    '''
    cmd_bytes = self.make_command_startRow(asicNum,startrow)
    ack = self.send_command(cmd_bytes)
    return ack

def make_command_lastRow(self,asicNum,lastrow):
    '''
    make the command to select the last row
    '''
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETASICSELLASTROW_ID,0x00)
    cmd_bytes_list.append(  (lastrow & 0xF0) >> 4           )
    cmd_bytes_list.append( ((lastrow & 0x0F) << 4 ) |  0x07 )
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)
    return self.make_communication_packet(cmd_bytes_list)

def send_lastRow(self,asicNum,lastrow):
    '''
    send the select row command
    '''
    cmd_bytes = self.make_command_lastRow(asicNum,lastrow)
    ack = self.send_command(cmd_bytes)
    return ack

def make_command_setColumn(self,asicNum,column):
    '''
    make the command to set the column
    '''
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETASICSETCOLUMN_ID,0x00)
    cmd_bytes_list.append(0x00)
    cmd_bytes_list.append( ((column & 0xF) << 4) |  0x05 )
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)
    return self.make_communication_packet(cmd_bytes_list)

def send_setColumn(self,asicNum,column):
    '''
    send the select set the column
    '''
    cmd_bytes = self.make_command_lastRow(asicNum,lastrow)
    ack = self.send_command(cmd_bytes)
    return ack

def make_command_CycleRawMode(self,asicNum,undersampling):
    '''
    make the command to set mode to Cycle Raw Mode (must give undersampling)
    '''
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETCYCLERAWMODE_ID,0x0B)
    cmd_bytes_list.append( (undersampling & 0xFF00) >> 8)
    cmd_bytes_list.append( (undersampling & 0x00FF)     )
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)
    return self.make_communication_packet(cmd_bytes_list)

def send_CycleRawMode(self,asicNum,undersampling):
    '''
    send the command to set the Cycle Raw Mode
    '''
    cmd_bytes = self.make_command_CycleRawMode(asicNum,undersampling)
    ack = self.send_command(cmd_bytes)
    return ack

def make_command_AsicConf(self,asicNum,signalID,state):
    '''
    make the command to configure the ASIC
    '''
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETASICCONF_ID,0x0D)
    cmd_bytes_list.append( (signalID & 0xFF) )
    cmd_bytes_list.append( (state & 0xFF   ) )
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)
    return self.make_communication_packet(cmd_bytes_list)

def send_AsicConf(self,asicNum,signalID,state):
    '''
    send the command to configure the ASIC
    '''
    cmd_bytes = self.make_command_AsicConf(asicNum,signalID,state)
    ack = self.send_command(cmd_bytes)
    return ack
    
def make_command_offsetTable(self,asicNum,offsetTable):
    '''
    make the command to configure the DAC offsets
    '''
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETOFFSETTABLE_ID,0x22)
    for val in offsetTable:
        ADU = self.offsetDACvalue2ADU(val)
        cmd_bytes_list.append( (ADU & 0xFF00) >> 8 )
        cmd_bytes_list.append( (ADU & 0x00FF)      )
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)
    return self.make_communication_packet(cmd_bytes_list)

def send_offsetTable(self,asicNum,offsetTable):
    '''
    send the DAC offsets
    '''
    cmd_bytes = self.make_command_offsetTable(asicNum,offsetTable)
    ack = self.send_command(cmd_bytes)
    return ack
    
def make_command_feedbackTable(self,asicNum,feedbackTable):
    '''
    make the command to configure the DAC feedback offsets
    '''
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_SETFEEDBACKTABLE_ID,0x22)
    for val in feedbackTable:
        ADU = self.feedbackDACvalue2ADU(val)
        cmd_bytes_list.append( (ADU & 0xFF00) >> 8 )
        cmd_bytes_list.append( (ADU & 0x00FF)      )
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)
    return self.make_communication_packet(cmd_bytes_list)

def send_feedbackTable(self,asicNum,feedbackTable):
    '''
    send the DAC feedback offsets
    '''
    cmd_bytes = self.make_command_feedbackTable(asicNum,feedbackTable)
    ack = self.send_command(cmd_bytes)
    return ack

def make_command_configurePID(self,asicNum,P,I,D):
    '''
    make the command to configure the feedback proportional-integral-derivative feedback loop
    '''
    cmd_bytes_list = self.make_frontend_preamble(asicNum,self.MULTINETQUICMANAGER_CONFIGUREPID_ID,0x13)
    cmd_bytes_list.append( (P & 0xFF00) >> 8 )
    cmd_bytes_list.append( (P & 0x00FF)      )
    cmd_bytes_list.append( (I & 0xFF00) >> 8 ) 
    cmd_bytes_list.append( (I & 0x00FF)      )
    cmd_bytes_list.append( (D & 0xFF00) >> 8 ) 
    cmd_bytes_list.append( (D & 0x00FF)      )
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)
    return self.make_communication_packet(cmd_bytes_list)

def send_configurePID(self,asicNum,P,I,D):
    '''
    send the DAC feedback offsets
    '''
    cmd_bytes = self.make_command_configurePID(asicNum,P,I,D)
    ack = self.send_command(cmd_bytes)
    return ack

