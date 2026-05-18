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
from qubichk.utilities import get_known_hosts, make_errmsg
known_hosts = get_known_hosts()
dome_server = known_hosts['dome']

def get_dome_status():
    '''
    get the status of the dome
    '''
    url = 'http://%s/awp/OwnWebsites/Script/StartOpti.json' % dome_server
    values = {}
    values['ok'] = False
    values['error'] = 'NONE'

    try:
        website = urlopen(url,timeout=5)
    except:
        values['error'] = make_errmsg('could not get dome status:')
        return values

    pg = website.read()

    try:
        json = eval(pg)
    except:
        values['error'] = make_errmsg('could not interpret dome contents')
        return values

    if 'val' not in json.keys():
        values['error'] = 'no values in JSON file'
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

    values['status'] = val_list[0]
    values['Puerta A'] = val_list[1]
    values['Puerta B'] = val_list[2]
    values['RPM A'] = val_list[3]
    values['RPM B'] = val_list[4]
    values['Current A'] = val_list[5]
    values['Current B'] = val_list[6]
    values['all'] = val_list

    if values['Puerta A']<24 and values['Puerta B']<24:
        values['dome state'] = 'OPEN'
    else:
        values['dome state'] = 'CLOSED'
    
    values['ok'] = True
    
    return values


