'''
$Id: dispatcher_id.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 13 Aug 2025 12:09:59 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

dispatcher top-level IDs for communication packets
'''
def assign_dispatcher_IDs(self):
    '''
    assign the dispatcher lookup table dictionaries
    '''
    self.dispatcher_ID = {}
    self.dispatcher_ID['SEND_TC_TO_SUBSYS_ID'] = 0xC0
    self.dispatcher_ID['CUSTOM_TC_ID'] = 0xD0
    self.dispatcher_ID['INTERN_TC_ID'] = 0xD1
    self.dispatcher_ID['CONF_DISPATCHER_TC_ID'] = 0xB0
    self.dispatcher_ID['DISPATCHER_ACK_TM_ID'] = 0xBB
    self.dispatcher_ID['DISPATCHER_PARAM_REQUEST_TM_ID'] = 0xBC
    
    # reverse lookup
    self.dispatcher_IDname = {}
    for key in self.dispatcher_ID.keys():
        code_num = self.dispatcher_ID[key]
        self.dispatcher_IDname[code_num] = key


    self.command_ID = {}
    self.command_ID['MULTINETQUICMANAGER_ID'] = 2
    self.command_ID['MULTINETQUICMANAGER_SETFEEDBACKTABLE_ID'] = 1
    self.command_ID['MULTINETQUICMANAGER_SETMASK_ID'] = 3
    self.command_ID['MULTINETQUICMANAGER_SETNSAMPLE_ID'] = 5
    self.command_ID['MULTINETQUICMANAGER_SETACQMODE_ID'] = 9
    self.command_ID['MULTINETQUICMANAGER_SETCYCLERAWMODE_ID'] = 11
    self.command_ID['MULTINETQUICMANAGER_SETASICCONF_ID'] = 13
    self.command_ID['MULTINETQUICMANAGER_GETSTATUS_ID'] = 14
    self.command_ID['MULTINETQUICMANAGER_SETOFFSETTABLE_ID'] = 20
    self.command_ID['MULTINETQUICMANAGER_CONFIGUREPID_ID'] = 21
    self.command_ID['MULTINETQUICMANAGER_ACTIVATEPID_ID'] = 22
    self.command_ID['MULTINETQUICMANAGER_SETTESDAC_CONTINUE_ID'] = 23
    self.command_ID['MULTINETQUICMANAGER_SETTESDAC_SINUS_ID'] = 25
    self.command_ID['MULTINETQUICMANAGER_SETASICAPOL_ID'] = 51
    self.command_ID['MULTINETQUICMANAGER_SETASICSPOL_ID'] = 52
    self.command_ID['MULTINETQUICMANAGER_SETASICVICM_ID'] = 53
    self.command_ID['MULTINETQUICMANAGER_SETASICVOCM_ID'] = 54
    self.command_ID['MULTINETQUICMANAGER_SETASICSETCOLUMN_ID'] = 55
    self.command_ID['MULTINETQUICMANAGER_SETASICSELSTARTROW_ID'] = 56
    self.command_ID['MULTINETQUICMANAGER_SETASICSELLASTROW_ID'] = 57
    self.command_ID['MULTINETQUICMANAGER_SETASICINIB_ID'] = 60
    self.command_ID['MULTINETQUICMANAGER_SETFEEDBACKRELAY_ID'] = 61
    self.command_ID['MULTINETQUICMANAGER_SETAPLITUDE_ID'] = 63 # this is a guess.  In fact, these secondary ID's don't seem to be used

    # reverse lookup
    self.command_name = {}
    for key in self.command_ID.keys():
        code_num = self.command_ID[key]
        self.command_name[code_num] = key
    
    return
