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

    # reverse lookup
    self.dispatcher_IDname = {}
    for key in self.dispatcher_ID.keys():
        code_num = self.dispatcher_ID[key]
        self.dispatcher_IDname[code_num] = key


    return
