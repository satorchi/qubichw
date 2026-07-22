'''
$Id: dome.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 09 Apr 2026 19:53:33 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

get the dome status
'''
from urllib.request import urlopen
from qubichk.utilities import get_known_hosts
from satorchipy.utilities import make_errmsg
known_hosts = get_known_hosts()
dome_server = known_hosts['dome']
value_names = {0:'Manual B',
               1:'Puerta A',
               2:'Puerta B',
               3:'Current A',
               5:'RPM A',
               6:'Alarm',
               7:'Current B',
               8:'Manual A',
               9:'RPM B'}

def get_dome_status():
    '''
    get the status of the dome
    '''
    url = 'http://%s/awp/OwnWebsites/Script/StartOpti.json' % dome_server
    values = {}
    values['ok'] = False
    values['error'] = 'NONE'
    values['message'] = 'NO INFO'

    try:
        website = urlopen(url,timeout=5)
    except:
        values['error'] = make_errmsg('could not get dome status:')
        values['message'] = 'server unreachable'
        return values

    pg = website.read()

    try:
        json = eval(pg)
    except:
        values['error'] = make_errmsg('could not interpret dome contents')
        values['message'] = 'could not interpret'
        return values

    if 'val' not in json.keys():
        values['error'] = 'no values in JSON file'
        values['message'] = 'no values in JSON'
        return values

    val_str = json['val']
    val_list = []
    len_str = json['len']
    len_list = len_str.split(';')
    idx = 0
    for lctr,l_str in enumerate(len_list):
        l = eval(l_str)
        idx_end = idx + l
        hex_str = '0x'+ val_str[idx:idx_end].ljust(4,'0')
        try:
            hex_val = eval(hex_str)
        except:
            continue
        val_list.append(hex_val)
        idx = idx_end

        if lctr in value_names.keys():
            valname = value_names[lctr]
        else:
            valname = 'unknown %i' % lctr
        values[valname] = hex_val

    if values['Puerta A']<24 and values['Puerta B']<24:
        values['dome state'] = 'OPEN'
    else:
        values['dome state'] = 'CLOSED'

    msg = '%.1f, %.1f: %s' % (values['Puerta A'],values['Puerta B'],values['dome state'])
    values['message'] = msg
    
    values['ok'] = True
    
    return values


