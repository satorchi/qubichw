'''
$Id: __init__.py <pystudio>
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 23 Jul 2025 15:24:58 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

package to communicate with the QubicStudio dispatcher

send a command to the QubicStudio dispatcher
send to port 3002 on QubicStudio

see email from Wilfried:  19 Apr 2022 16:39:24

STX  ( 8 bits)  start of transmission = 0x55
CN   (16 bits)  counter
SIZE (32 bits)  size of the data section of the command
ID   ( 8 bits)  ID of the command (INTERN_TC is 0xD1)
DATA ( N bits)  the body of the command (including 16 bits for subID)
EOT  ( 8 bits)  end of transmission = 0xAA

to stop an ongoing backup:
0x55 0x00 0x00 0x00 0x00 0x00 0x05 0xD1  0x00 0x05 backupId_MSB backupId_LSB 0xAA
STX  CN        SIZE                ID    DATA                                EOT

in the Data section:
subID (16 bits) 0x0005 for "stop backup" (stop data acquisition)
backupsID MSB (8 bits)  (is this a free parameter?)
backupsID LSB (8 bits)  (is this a free parameter?)


to start a backup:
STX  CN        SIZE                ID    DATA                                EOT
0x55 0x00 0x00 0x00 0x00 0x00 0xNN 0xD1  0x00 0x04 session_name 0 comment 0  0xAA

in the Data section:
subID (16 bits) 0x0004 for "start backup" (start data acquisition)
session_name (N bits): ascii characters




see in QubicStudio source code: TVirtualCommandEncode.cpp, QDispatcherTCByteArray.cpp
                                methods: startNewInternTC, sendInternTC...

'''
class pystudio:
    verbosity = 1 # class variable.  You can change this before instantiating an object
    __object_type__ = 'pystudio'

    DISPATCHER_STX = 0x55
    END_COMMUNICATION = 0xAA
    SEND_TC_TO_SUBSYS_ID = 0xC0
    CUSTOM_TC_ID = 0xD0
    INTERN_TC_ID = 0xD1

    MULTINETQUICMANAGER_ID = 2
    MULTINETQUICMANAGER_ACTIVATEPID_ID = 22
    MULTINETQUICMANAGER_SETTESDAC_CONTINUE_ID = 23
    MULTINETQUICMANAGER_SETTESDAC_SINUS_ID = 25

    MULTINETQUICMANAGER_GETSTATUS_ID = 14
    MULTINETQUICMANAGER_SETFEEDBACKRELAY_ID = 61
    MULTINETQUICMANAGER_SETAPLITUDE_ID = 63 # this is a guess
    
    START_ACQUISITION_COMMAND = 4
    STOP_ACQUISITION_COMMAND = 5
    
    DISPATCHER_PORT = 3002

    dispatcher_socket = None
    backupsID = None
    command_counter = 0
    chunksize = 2**20

    from .communication import\
        interpret_communication,\
        print_acknowledgement,\
        subscribe_dispatcher,\
        unsubscribe,\
        send_command,\
        make_preamble,\
        make_communication_packet

    from .acquisition import\
        make_backupsID,\
        make_command_startAcquisition,\
        send_startAcquisition,\
        make_command_stopAcquisition,\
        send_stopAcquisition

    from .frontend import\
        asic_qsnumber,\
        make_command_startstopFLL,\
        send_startFLL,\
        send_stopFLL,\
        Voffset2ADU,\
        amplitude2ADU,\
        make_frontend_preamble,\
        make_frontend_suffix,\
        make_command_TESDAC_SINUS,\
        send_TESDAC_SINUS,\
        make_command_TESDAC_CONTINUOUS,\
        send_TESDAC_CONTINUOUS,\
        make_command_get_frontend_status,\
        get_frontend_status,\
        make_command_FeedbackRelay,\
        send_FeedbackRelay,\
        make_command_Aplitude,\
        send_Aplitude

    from .sequence import\
        set_bath_temperature,\
        do_IV_measurement,\
        do_NEP_measurement,\
        do_skydip,\
        do_scan
    

    
    

    
