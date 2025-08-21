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

parm_list = ['NETQUIC_HeaderTM_ASIC_ID',
             'DISP_LogbookFilename_ID',
             'QUBIC_TESDAC_Shape_ID',
             'QUBIC_TESDAC_Offset_ID',
             'QUBIC_TESDAC_Amplitude_ID',
             'QUBIC_Rfb_ID',
             'QUBIC_FLL_State_ID',
             'QUBIC_FLL_P_ID',
             'QUBIC_FLL_I_ID',
             'QUBIC_FLL_D_ID',
             'ASIC_Spol_ID',
             'ASIC_Apol_ID'
             ]

txt = {}
txt['common'] = []
for idx in range(dispatcher.NASIC):
    key = 'ASIC %2i' % (idx+1)
    txt[key] = []


    
for parm_name in parm_list:
    vals = dispatcher.send_request(parameterList=[parm_name])

    # save response for debugging
    fname = '%s_request.dat' % parm_name
    h = open(fname,'wb')
    h.write(vals['bytes'])
    h.close()
    
    if parm_name not in vals.keys(): continue

    parm_vals = vals[parm_name]['value']
    
    if isinstance(parm_vals,str):
        line = '%s = %s' % (parm_vals)
        txt['common'].append(line)
        continue

    if isinstance(parm_vals,np.ndarray):
        if parm_vals.dtype=='float':
            for idx in range(dispatcher.NASIC):
                val = parm_vals[idx]
                key = 'ASIC %2i' % (idx+1)
                line = '%s = %.2f' % (parm_name,val)
                txt[key].append(line)
            continue
                
        if parm_vals.dtype=='int':
            for idx in range(dispatcher.NASIC):
                val = parm_vals[idx]
                key = 'ASIC %2i' % (idx+1)
                line = '%s = %i' % (parm_name,val)
                txt[key].append(line)
            continue
            
    if parm_vals is None:
        line = '%s = %s' % (parm_name,vals[parm_name]['text'])
        txt['common'].append(line)
        continue
    
    line = '%s = %s' % parm_vals
    txt['common'].append(line)

line = ' QUBIC FRONTEND STATUS '.center(80,'*'))
lines = [line]
lines += txt['common']

for idx in range(dispatcher.NASIC):
    key = 'ASIC %2i' % (idx+1)
    ttl = ' %s ' % key
    line = '\n'+ttl.center(80,'*')
    lines.append(line)
    lines += txt[key]

msg = '\n'.join(lines)
print(msg)

