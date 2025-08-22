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
import numpy as np
from pystudio import pystudio

dispatcher = pystudio()
ack = dispatcher.subscribe_dispatcher()

parm_list = ['DISP_LogbookFilename_ID',
             'QUBIC_TESDAC_Shape_ID',
             'QUBIC_TESDAC_Offset_ID',
             'QUBIC_TESDAC_Amplitude_ID',
             'QUBIC_TESDAC_Sunder_ID',
             'QUBIC_FLL_State_ID',
             'QUBIC_FLL_P_ID',
             'QUBIC_FLL_I_ID',
             'QUBIC_FLL_D_ID',
             'ASIC_Spol_ID',
             'ASIC_Apol_ID',
             'ASIC_Vicm_ID',
             'ASIC_Vocm_ID',
             'QUBIC_Nsample_ID',
             'QUBIC_Nsamples_ID',
             'QUBIC_rawMaskSamples_ID',
             'QUBIC_relayStates_ID'
             ]

# do the full list to see what we've got.  THIS IS TEMPORARY
# parm_list = list(dispatcher.parameterstable.keys())

# try to find Aplitude
parm_list = ['PARAMETER_UNKNOWN_10551_ID',
             'PARAMETER_UNKNOWN_10552_ID',
             'PARAMETER_UNKNOWN_10553_ID',
             'PARAMETER_UNKNOWN_10554_ID',
             'PARAMETER_UNKNOWN_10555_ID',
             'PARAMETER_UNKNOWN_10556_ID',
             'PARAMETER_UNKNOWN_10557_ID',
             'PARAMETER_UNKNOWN_10558_ID',
             'PARAMETER_UNKNOWN_10559_ID',
             'PARAMETER_UNKNOWN_10560_ID']

def get_frontend_status():
    '''
    build a nice text message containing the frontend status
    '''
    
    txt = {}
    txt['common'] = []
    for idx in range(16):
        key = 'ASIC %2i' % (idx+1)
        txt[key] = []

    txt['ERROR'] = []

    # it seems the request only works for one parameter at a time,
    # even though it seems to be built to return multiple parameters
    for parm_name in parm_list:
        vals = dispatcher.send_request(parameterList=[parm_name])
        if 'bytes' not in vals.keys():
            txt['ERROR'].append(parm_name+'\n   ')
            txt['ERROR'].append('\n   '.join(vals['ERROR']))
            continue

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
    for idx in range(dispatcher.NASIC):
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

if __name__=='__main__':
    msg = get_frontend_status()
    print(msg)

