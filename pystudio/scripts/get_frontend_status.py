#!/usr/bin/env python3
'''
$Id: get_frontend_status.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 21 Aug 2025 14:33:58 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

get the status of the frontend
'''

from pystudio import pystudio

dispatcher = pystudio()
ack = dispatcher.subscribe_dispatcher()

parm_list = ['ASIC_Spol_ID',
             'ASIC_Apol_ID',
             'QUBIC_TESDAC_Shape_ID',
             'QUBIC_TESDAC_Offset_ID',
             'QUBIC_TESDAC_Amplitude_ID',
             'QUBIC_Rfb_ID',
             'QUBIC_FLL_State_ID',
             'QUBIC_FLL_P_ID',
             'QUBIC_FLL_I_ID',
             'QUBIC_FLL_D_ID'
             ]

for parm_name in parm_list:
    vals = dispatcher.send_request(parameterList=[parm_name])
    fname = '%s_request.dat' % parm_name
    h = open(fname,'wb')
    h.write(vals['bytes'])
    h.close()
    
    if parm_name not in vals.keys(): continue

    if parm_name.find('Offset')>0 or parm_name.find('Amplitude')>0:
        print('%s = %.2f' % (parm_name,vals[parm_name]['physical']))
        continue

    if parm_name.find('Spol_ID')>0:
        for idx in range(dispatcher.NASIC):
            print('%s ASIC %2i = %i' % (parm_name,(idx+1),vals[parm_name]['value'][idx]))
        continue

    print('%s = %s' % (parm_name,vals[parm_name]['text']))

    
